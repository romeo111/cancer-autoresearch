"""Tests for translate_client — DeepL + LibreTranslate + fallback + cache.

Uses httpx MockTransport so no real network calls happen. Verifies:

- DeepL request shape (auth header, target_lang upper, text in body)
- LibreTranslate request shape (lowercase target, optional auto source)
- HTTP errors mapped to TranslateError (with quota-specific 456 path)
- FallbackTranslateClient routes around primary failures
- CachedTranslateClient produces correct on-disk record + repeat call
  hits cache (no network)
- build_translate_client returns the expected stack based on env vars
- CHARTER §8.3 compliance: cache record carries machine_translated=true
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from knowledge_base.clients.translate_client import (
    CachedTranslateClient,
    DeepLClient,
    FallbackTranslateClient,
    LibreTranslateClient,
    TranslateError,
    build_translate_client,
)


# ── Helpers ───────────────────────────────────────────────────────────────


def _deepl_transport(captured: dict, *, status: int = 200, text_out: str = "Привіт"):
    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["headers"] = dict(request.headers)
        captured["body"] = json.loads(request.content.decode("utf-8"))
        if status != 200:
            return httpx.Response(status, json={"message": "err"})
        return httpx.Response(200, json={
            "translations": [{"detected_source_language": "EN", "text": text_out}]
        })
    return httpx.MockTransport(handler)


def _libre_transport(captured: dict, *, status: int = 200, text_out: str = "Hello"):
    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content.decode("utf-8"))
        if status != 200:
            return httpx.Response(status, json={"error": "err"})
        return httpx.Response(200, json={"translatedText": text_out})
    return httpx.MockTransport(handler)


def _patch_http_client(monkeypatch, transport: httpx.MockTransport) -> None:
    """Replace httpx.Client constructor so any client uses our mock transport."""
    real_init = httpx.Client.__init__

    def fake_init(self, *args, **kwargs):
        kwargs["transport"] = transport
        real_init(self, *args, **kwargs)

    monkeypatch.setattr(httpx.Client, "__init__", fake_init)


# ── DeepL ─────────────────────────────────────────────────────────────────


def test_deepl_translate_success(monkeypatch):
    captured: dict = {}
    _patch_http_client(monkeypatch, _deepl_transport(captured, text_out="Привіт світ"))

    client = DeepLClient(api_key="test-key:fx")
    out = client.translate("Hello world", target_lang="uk", source_lang="en")

    assert out == "Привіт світ"
    assert captured["body"]["text"] == ["Hello world"]
    assert captured["body"]["target_lang"] == "UK"
    assert captured["body"]["source_lang"] == "EN"
    assert captured["headers"]["authorization"] == "DeepL-Auth-Key test-key:fx"
    # `:fx` suffix → free endpoint
    assert "api-free.deepl.com" in captured["url"]


def test_deepl_uses_pro_endpoint_for_non_fx_keys(monkeypatch):
    captured: dict = {}
    _patch_http_client(monkeypatch, _deepl_transport(captured))
    DeepLClient(api_key="paid-key-without-fx").translate("Hi", "uk")
    assert "api.deepl.com" in captured["url"]
    assert "api-free" not in captured["url"]


def test_deepl_quota_exceeded_maps_to_translate_error(monkeypatch):
    captured: dict = {}
    _patch_http_client(monkeypatch, _deepl_transport(captured, status=456))
    client = DeepLClient(api_key="k:fx")
    with pytest.raises(TranslateError, match="quota"):
        client.translate("Hi", "uk")


def test_deepl_auth_failure_maps_to_translate_error(monkeypatch):
    captured: dict = {}
    _patch_http_client(monkeypatch, _deepl_transport(captured, status=403))
    client = DeepLClient(api_key="k:fx")
    with pytest.raises(TranslateError, match="auth"):
        client.translate("Hi", "uk")


def test_deepl_missing_key_raises():
    with pytest.raises(TranslateError, match="DEEPL_API_KEY"):
        DeepLClient(api_key="")


# ── LibreTranslate ────────────────────────────────────────────────────────


def test_libretranslate_translate_success(monkeypatch):
    captured: dict = {}
    _patch_http_client(monkeypatch, _libre_transport(captured, text_out="Hello world"))

    client = LibreTranslateClient(url="http://lt.local:5000")
    out = client.translate("Привіт світ", target_lang="EN", source_lang="UK")

    assert out == "Hello world"
    # LibreTranslate uses lowercase codes
    assert captured["body"]["target"] == "en"
    assert captured["body"]["source"] == "uk"
    assert captured["body"]["q"] == "Привіт світ"
    assert captured["body"]["format"] == "text"


def test_libretranslate_defaults_source_to_auto(monkeypatch):
    captured: dict = {}
    _patch_http_client(monkeypatch, _libre_transport(captured))
    LibreTranslateClient(url="http://lt:5000").translate("Hi", "uk")
    assert captured["body"]["source"] == "auto"


def test_libretranslate_includes_api_key_when_set(monkeypatch):
    captured: dict = {}
    _patch_http_client(monkeypatch, _libre_transport(captured))
    LibreTranslateClient(url="http://lt:5000", api_key="lt-key").translate("Hi", "uk")
    assert captured["body"]["api_key"] == "lt-key"


def test_libretranslate_http_error_maps_to_translate_error(monkeypatch):
    captured: dict = {}
    _patch_http_client(monkeypatch, _libre_transport(captured, status=500))
    client = LibreTranslateClient(url="http://lt:5000")
    with pytest.raises(TranslateError):
        client.translate("Hi", "uk")


# ── Fallback ──────────────────────────────────────────────────────────────


class _StubClient:
    """Minimal in-memory client for fallback / cache tests."""
    def __init__(self, name: str, *, raises: bool = False, output: str = "STUB"):
        self.name = name
        self.raises = raises
        self.output = output
        self.calls = 0

    def translate(self, text: str, target_lang: str, source_lang=None) -> str:
        self.calls += 1
        if self.raises:
            raise TranslateError(f"{self.name} simulated failure")
        return f"{self.output}({text}→{target_lang})"


def test_fallback_uses_primary_when_ok():
    primary = _StubClient("primary", output="P")
    secondary = _StubClient("secondary", output="S")
    fb = FallbackTranslateClient(primary=primary, secondary=secondary)
    assert fb.translate("Hi", "uk") == "P(Hi→uk)"
    assert primary.calls == 1
    assert secondary.calls == 0


def test_fallback_routes_to_secondary_on_translate_error():
    primary = _StubClient("primary", raises=True)
    secondary = _StubClient("secondary", output="S")
    fb = FallbackTranslateClient(primary=primary, secondary=secondary)
    assert fb.translate("Hi", "uk") == "S(Hi→uk)"
    assert primary.calls == 1
    assert secondary.calls == 1


# ── Cache ─────────────────────────────────────────────────────────────────


def test_cache_writes_full_record_with_charter_compliance_flag(tmp_path: Path):
    inner = _StubClient("deepl", output="UA-text")
    cache = CachedTranslateClient(inner, cache_dir=tmp_path)
    out = cache.translate("Hello", "uk", "en")
    assert out == "UA-text(Hello→uk)"

    # Exactly one cache file, contains required fields per CHARTER §8.3
    files = list(tmp_path.glob("*.json"))
    assert len(files) == 1
    record = json.loads(files[0].read_text(encoding="utf-8"))
    assert record["source_text"] == "Hello"
    assert record["translation"] == "UA-text(Hello→uk)"
    assert record["source_lang"] == "en"
    assert record["target_lang"] == "uk"
    assert record["engine"] == "deepl"  # propagates inner.name
    assert record["machine_translated"] is True
    assert record["translated_at"]


def test_cache_hit_skips_inner_call(tmp_path: Path):
    inner = _StubClient("deepl")
    cache = CachedTranslateClient(inner, cache_dir=tmp_path)
    cache.translate("Hello", "uk", "en")
    cache.translate("Hello", "uk", "en")
    cache.translate("Hello", "uk", "en")
    assert inner.calls == 1


def test_cache_key_includes_source_lang(tmp_path: Path):
    """Same text + target_lang but different source_lang → different cache entries."""
    inner = _StubClient("deepl")
    cache = CachedTranslateClient(inner, cache_dir=tmp_path)
    cache.translate("Hello", "uk", "en")
    cache.translate("Hello", "uk", "de")
    assert inner.calls == 2
    assert len(list(tmp_path.glob("*.json"))) == 2


def test_cache_handles_corrupt_file_gracefully(tmp_path: Path):
    inner = _StubClient("deepl")
    cache = CachedTranslateClient(inner, cache_dir=tmp_path)
    cache.translate("Hello", "uk", "en")
    # Corrupt the only cache file
    f = next(tmp_path.glob("*.json"))
    f.write_text("not valid json", encoding="utf-8")
    # Re-fetch should not crash
    out = cache.translate("Hello", "uk", "en")
    assert out
    assert inner.calls == 2


def test_empty_string_passthrough(tmp_path: Path):
    """Empty text → return as-is, never touch network or cache."""
    inner = _StubClient("deepl")
    cache = CachedTranslateClient(inner, cache_dir=tmp_path)
    assert cache.translate("", "uk", "en") == ""
    assert inner.calls == 0
    assert not list(tmp_path.glob("*.json"))


# ── Factory ───────────────────────────────────────────────────────────────


def test_build_returns_libretranslate_only_without_deepl_key(monkeypatch, tmp_path: Path):
    monkeypatch.delenv("DEEPL_API_KEY", raising=False)
    monkeypatch.setenv("LIBRETRANSLATE_URL", "http://lt:5000")
    client = build_translate_client(use_cache=False, libre_url="http://lt:5000")
    # Without DeepL key, factory returns a bare LibreTranslate client
    assert isinstance(client, LibreTranslateClient)


def test_build_wraps_cache_by_default(monkeypatch, tmp_path: Path):
    monkeypatch.delenv("DEEPL_API_KEY", raising=False)
    client = build_translate_client(
        use_cache=True,
        cache_dir=tmp_path,
        libre_url="http://lt:5000",
    )
    assert isinstance(client, CachedTranslateClient)


def test_build_full_chain_with_both_engines(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("DEEPL_API_KEY", "test:fx")
    monkeypatch.setenv("LIBRETRANSLATE_URL", "http://lt:5000")
    client = build_translate_client(use_cache=True, cache_dir=tmp_path)
    assert isinstance(client, CachedTranslateClient)
    assert isinstance(client.inner, FallbackTranslateClient)
    assert isinstance(client.inner.primary, DeepLClient)
    assert isinstance(client.inner.secondary, LibreTranslateClient)


# ── Glossary (translation memory) ─────────────────────────────────────────


from knowledge_base.clients.translate_client import (
    GlossaryTranslateClient,
    build_full_stack,
    translate_for_ingestion,
    DEFAULT_SKIP_PATTERNS,
)


@pytest.mark.parametrize("text", [
    "DRUG-RITUXIMAB", "TEST-CBC", "REG-VRD", "IND-MM-1L-VRD",
    "RF-BULKY-DISEASE", "CI-HBV-NO-PROPHYLAXIS", "MON-BR-REGIMEN",
    "WORKUP-SUSPECTED-LYMPHOMA", "ALGO-MM-1L", "BIO-MM-CYTOGENETICS-HR",
    "SRC-NCCN-MM-2025", "OQ-HBV-SEROLOGY",
    "90 mg/m²", "1.3 mg/m²", "16 mg/kg", "375 mg/m²",
    "75%", "12.5 %", ">95%",
    "9699/3", "C88.4", "C90.0",
    "CD20", "BCL2", "MYC", "JAK2",
    "v0.1.0", "v1.0",
    "2026-04-25",
    "https://example.com/foo",
    "test_cbc.yaml", "build_site.py",
    "§15.2 C7", "§ 6.1",
])
def test_glossary_skips_protected_patterns(text):
    """Entity IDs, doses, codes etc. must not reach the translator."""
    inner = _StubClient("inner")
    g = GlossaryTranslateClient(inner)
    assert g.translate(text, "en", "uk") == text
    assert inner.calls == 0, f"glossary leaked '{text}' to inner translator"


def test_glossary_passes_through_real_text():
    inner = _StubClient("inner", output="EN")
    g = GlossaryTranslateClient(inner)
    out = g.translate("Лікар завантажує профіль пацієнта", "en", "uk")
    assert out.startswith("EN(")
    assert inner.calls == 1


def test_glossary_applies_term_overrides_after_translation():
    """Overrides enforce house-style on jargon the translator might mangle."""
    class FakeInner:
        name = "fake"
        def translate(self, text, target_lang, source_lang=None):
            # Simulate translator producing wrong jargon: "tumor council"
            return "discussion at tumor council about patient profile"
    g = GlossaryTranslateClient(FakeInner())
    out = g.translate("обговорення на тумор-борд про профіль пацієнта", "en", "uk")
    # Override map is keyed (uk,en); but the test simulates EN output that
    # already includes "patient profile" — should pass through. The
    # tumor-board override only fires when translator outputs UA→EN with
    # the source-side phrase appearing. We verify the substitution
    # mechanism by checking a known UA→EN pair below directly.
    assert "patient profile" in out

    # Direct UA term override path: source UA text with "тумор-борд",
    # inner returns it untranslated, override should map to "tumor board".
    class PassthroughInner:
        name = "fake"
        def translate(self, text, target_lang, source_lang=None):
            return text  # echo
    g2 = GlossaryTranslateClient(PassthroughInner())
    out2 = g2.translate("обговорення на тумор-борд", "en", "uk")
    assert "tumor board" in out2


def test_glossary_empty_input_passthrough():
    inner = _StubClient("inner")
    g = GlossaryTranslateClient(inner)
    assert g.translate("", "en", "uk") == ""
    assert g.translate("   ", "en", "uk") == "   "
    assert inner.calls == 0


def test_glossary_skip_patterns_can_be_overridden():
    """Caller can supply custom skip_patterns (e.g., for non-clinical
    domains)."""
    inner = _StubClient("inner", output="OUT")
    g = GlossaryTranslateClient(inner, skip_patterns=[r"FOO-\w+"])
    # FOO-X is now skipped; DRUG-X is NOT (overridden patterns replace defaults)
    assert g.translate("FOO-BAR", "en", "uk") == "FOO-BAR"
    assert g.translate("DRUG-RITUXIMAB", "en", "uk").startswith("OUT(")


# ── build_full_stack ──────────────────────────────────────────────────────


def test_build_full_stack_layers_cache_glossary_fallback(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("DEEPL_API_KEY", "test:fx")
    monkeypatch.setenv("LIBRETRANSLATE_URL", "http://lt:5000")
    stack = build_full_stack(cache_dir=tmp_path)
    # cache → glossary → fallback(deepl, libretranslate)
    assert isinstance(stack, CachedTranslateClient)
    assert isinstance(stack.inner, GlossaryTranslateClient)
    assert isinstance(stack.inner.inner, FallbackTranslateClient)
    assert isinstance(stack.inner.inner.primary, DeepLClient)
    assert isinstance(stack.inner.inner.secondary, LibreTranslateClient)


def test_build_full_stack_without_glossary_or_cache(monkeypatch, tmp_path: Path):
    monkeypatch.delenv("DEEPL_API_KEY", raising=False)
    stack = build_full_stack(use_cache=False, use_glossary=False, libre_url="http://lt:5000")
    assert isinstance(stack, LibreTranslateClient)


# ── translate_for_ingestion ───────────────────────────────────────────────


def test_translate_for_ingestion_returns_metadata_record():
    """Returns a YAML-embeddable record with CHARTER §8.3 metadata flags."""
    record = translate_for_ingestion(
        "Bendamustine + Rituximab",
        source_lang="en", target_lang="uk",
        client=_StubClient("deepl", output="UA"),
    )
    assert record["source_text"] == "Bendamustine + Rituximab"
    assert record["translation"].startswith("UA(")
    assert record["source_lang"] == "en"
    assert record["target_lang"] == "uk"
    assert record["engine"] == "deepl"
    assert record["machine_translated"] is True
    assert record["needs_clinical_review"] is True
    assert record["translated_at"]
