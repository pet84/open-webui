"""
title: OpenWebUI Skills Manager Tool
author: Fu-Jie
author_url: https://github.com/Fu-Jie/openwebui-extensions
funding_url: https://github.com/open-webui
version: 0.2.1
openwebui_id: b4bce8e4-08e7-4f90-bea7-dc31d463a0bb
requirements:
description: Samostatný nástroj OpenWebUI pro správu vestavěných Skills v Workspace (výpis/zobrazení/instalace/vytvoření/aktualizace/smazání) pro libovolný model.
"""

import asyncio
import json
import logging
import re
import tempfile
import tarfile
import uuid
import zipfile
import urllib.request
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

try:
    from open_webui.models.skills import Skills, SkillForm, SkillMeta
except Exception:
    Skills = None
    SkillForm = None
    SkillMeta = None


TRANSLATIONS = {
    "cs-CZ": {
        "status_listing": "Vypsávám vaše skills...",
        "status_showing": "Načítám detail skillu...",
        "status_installing": "Instaluji skill z URL...",
        "status_installing_batch": "Instaluji {total} skill(ů)...",
        "status_discovering_skills": "Objevuji skills v {url}...",
        "status_creating": "Vytvářím skill...",
        "status_updating": "Aktualizuji skill...",
        "status_deleting": "Mažu skill...",
        "status_done": "Hotovo.",
        "status_list_done": "Nalezeno {count} skills ({active_count} aktivních).",
        "status_show_done": "Načten skill: {name}.",
        "status_install_done": "Nainstalován skill: {name}.",
        "status_install_overwrite_done": "Nainstalováno aktualizací existujícího: {name}.",
        "status_create_done": "Vytvořen skill: {name}.",
        "status_create_overwrite_done": "Aktualizován existující skill: {name}.",
        "status_update_done": "Aktualizován skill: {name}.",
        "status_delete_done": "Smazán skill: {name}.",
        "status_install_batch_done": "Dávková instalace dokončena: {succeeded} úspěšných, {failed} neúspěšných.",
        "err_unavailable": "Model OpenWebUI Skills není v tomto prostředí dostupný.",
        "err_user_required": "Je vyžadován kontext uživatele.",
        "err_name_required": "Název skillu je povinný.",
        "err_not_found": "Skill nenalezen.",
        "err_no_update_fields": "Neposkytnuta žádná pole k aktualizaci.",
        "err_url_required": "URL skillu je povinná.",
        "err_install_fetch": "Nepodařilo se stáhnout obsah skillu z URL.",
        "err_install_parse": "Nepodařilo se zpracovat balíček/obsah skillu.",
        "err_invalid_url": "Neplatná URL. Podporovány jsou pouze http(s) adresy.",
        "msg_created": "Skill byl úspěšně vytvořen.",
        "msg_updated": "Skill byl úspěšně aktualizován.",
        "msg_deleted": "Skill byl úspěšně smazán.",
        "msg_installed": "Skill byl úspěšně nainstalován.",
    },
}

FALLBACK_MAP = {
    "cs": "cs-CZ",
}


class Tools:
    """Vestavěné nástroje OpenWebUI pro správu životního cyklu skills."""

    class Valves(BaseModel):
        """Konfigurovatelné parametry pluginu."""

        SHOW_STATUS: bool = Field(
            default=True,
            description="Zda zobrazovat průběh operací.",
        )
        ALLOW_OVERWRITE_ON_CREATE: bool = Field(
            default=False,
            description="Povolit create_skill/install_skill přepsat skill se stejným názvem (výchozí).",
        )
        INSTALL_FETCH_TIMEOUT: float = Field(
            default=12.0,
            description="Timeout in seconds for URL fetch when installing a skill.",
        )

    def __init__(self):
        """Inicializace parametrů pluginu."""
        self.valves = self.Valves()

    def _resolve_language(self, user_language: str) -> str:
        """Převede kód jazyka uživatele na podporovaný klíč překladu."""
        value = str(user_language or "").strip()
        if not value:
            return "cs-CZ"

        normalized = value.replace("_", "-")

        if normalized in TRANSLATIONS:
            return normalized

        lower_to_lang = {k.lower(): k for k in TRANSLATIONS.keys()}
        if normalized.lower() in lower_to_lang:
            return lower_to_lang[normalized.lower()]

        if normalized in FALLBACK_MAP:
            return FALLBACK_MAP[normalized]

        lower_fallback = {k.lower(): v for k, v in FALLBACK_MAP.items()}
        if normalized.lower() in lower_fallback:
            return lower_fallback[normalized.lower()]

        base = normalized.split("-")[0].lower()
        return lower_fallback.get(base, "cs-CZ")

    def _t(self, lang: str, key: str, **kwargs) -> str:
        """Vrátí přeložený text pro klíč s bezpečným formátováním."""
        lang_key = self._resolve_language(lang)
        text = TRANSLATIONS.get(lang_key, TRANSLATIONS["cs-CZ"]).get(
            key, TRANSLATIONS["cs-CZ"].get(key, key)
        )
        if kwargs:
            try:
                text = text.format(**kwargs)
            except KeyError:
                pass
        return text

    async def _get_user_context(
        self,
        __user__: Optional[dict],
        __event_call__: Optional[Any] = None,
        __request__: Optional[Any] = None,
    ) -> Dict[str, str]:
        """Získá kontext uživatele včetně jazyka z frontendu."""
        if isinstance(__user__, (list, tuple)):
            user_data = __user__[0] if __user__ else {}
        elif isinstance(__user__, dict):
            user_data = __user__
        else:
            user_data = {}

        user_language = user_data.get("language", "en-US")

        if __request__ and hasattr(__request__, "headers"):
            accept_lang = __request__.headers.get("accept-language", "")
            if accept_lang:
                user_language = accept_lang.split(",")[0].split(";")[0]

        if __event_call__:
            try:
                js_code = """
                    try {
                        return (
                            document.documentElement.lang ||
                            localStorage.getItem('locale') ||
                            localStorage.getItem('language') ||
                            navigator.language ||
                            'en-US'
                        );
                    } catch (e) {
                        return 'en-US';
                    }
                """
                frontend_lang = await asyncio.wait_for(
                    __event_call__({"type": "execute", "data": {"code": js_code}}),
                    timeout=2.0,
                )
                if frontend_lang and isinstance(frontend_lang, str):
                    user_language = frontend_lang
            except Exception as e:
                logger.warning(f"Failed to retrieve frontend language: {e}")

        return {
            "user_id": str(user_data.get("id", "")).strip(),
            "user_name": user_data.get("name", "User"),
            "user_language": user_language,
        }

    async def _emit_status(
        self,
        emitter: Optional[Any],
        description: str,
        done: bool = False,
    ):
        """Odešle událost stavu do stavového řádku OpenWebUI, pokud je zapnuto."""
        if self.valves.SHOW_STATUS and emitter:
            await emitter(
                {
                    "type": "status",
                    "data": {"description": description, "done": done},
                }
            )

    def _require_skills_model(self):
        """Ověří, že jsou dostupné API modelu OpenWebUI Skills."""
        if Skills is None or SkillForm is None or SkillMeta is None:
            raise RuntimeError("skills_model_unavailable")

    def _user_skills(self, user_id: str, access: str = "read") -> List[Any]:
        """Načte skills uživatele pomocí modelu OpenWebUI Skills."""
        return Skills.get_skills_by_user_id(user_id, access) or []

    def _find_skill(
        self,
        user_id: str,
        skill_id: str = "",
        name: str = "",
    ) -> Optional[Any]:
        """Najde skill podle id nebo názvu (bez ohledu na velikost písmen) v rámci uživatele."""
        skills = self._user_skills(user_id, "read")
        target_id = (skill_id or "").strip()
        target_name = (name or "").strip().lower()

        for skill in skills:
            sid = str(getattr(skill, "id", "") or "")
            sname = str(getattr(skill, "name", "") or "")
            if target_id and sid == target_id:
                return skill
            if target_name and sname.lower() == target_name:
                return skill
        return None

    def _extract_folder_name_from_url(self, url: str) -> str:
        """Získá název složky z cesty GitHub URL.
        Příklady:
          - https://github.com/.../tree/main/skills/xlsx -> xlsx
          - https://github.com/.../blob/main/skills/README.md -> skills
          - https://raw.githubusercontent.com/.../main/skills/README.md -> skills
        """
        try:
            # Remove query string and fragments
            path = url.split("?")[0].split("#")[0]
            # Get last path component
            parts = path.rstrip("/").split("/")
            if parts:
                last = parts[-1]
                # Skip if it's a file extension
                if "." not in last or last.startswith("."):
                    return last
                # Return parent directory if it's a filename
                if len(parts) > 1:
                    return parts[-2]
        except Exception:
            pass
        return ""

    async def _discover_skills_from_github_directory(
        self, url: str, lang: str
    ) -> List[str]:
        """
        Objeví všechny podsložky se skills z GitHub tree URL.
        Používá GitHub API pro výpis obsahu adresáře.

        Příklad: https://github.com/anthropics/skills/tree/main/skills
        Vrací: Seznam URL jednotlivých skill složek
        """
        skill_urls = []
        match = re.match(
            r"https://github\.com/([^/]+)/([^/]+)/tree/([^/]+)(/.*)?\Z", url
        )
        if not match:
            return skill_urls

        owner = match.group(1)
        repo = match.group(2)
        branch = match.group(3)
        path = match.group(4) or ""

        try:
            api_url = f"https://api.github.com/repos/{owner}/{repo}/contents{path}?ref={branch}"
            response_bytes = await self._fetch_bytes(api_url)
            contents = json.loads(response_bytes.decode("utf-8"))

            if isinstance(contents, list):
                for item in contents:
                    if item.get("type") == "dir":
                        subdir_name = item.get("name", "")
                        if subdir_name and not subdir_name.startswith("."):
                            subdir_url = f"https://github.com/{owner}/{repo}/tree/{branch}{path}/{subdir_name}"
                            skill_urls.append(subdir_url)

            skill_urls.sort()
        except Exception as e:
            logger.warning(
                f"Failed to discover skills from GitHub directory {url}: {e}"
            )

        return skill_urls

    def _resolve_github_tree_urls(self, url: str) -> List[str]:
        """Pro GitHub tree URL vrátí přímé URL souborů k vyzkoušení.

        Příklad: https://github.com/anthropics/skills/tree/main/skills/xlsx
        Vrací: [
            https://raw.githubusercontent.com/anthropics/skills/main/skills/xlsx/SKILL.md,
            https://raw.githubusercontent.com/anthropics/skills/main/skills/xlsx/README.md,
        ]
        """
        urls = []
        match = re.match(
            r"https://github\.com/([^/]+)/([^/]+)/tree/([^/]+)(/.*)?\Z", url
        )
        if match:
            owner = match.group(1)
            repo = match.group(2)
            branch = match.group(3)
            path = match.group(4) or ""
            base = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}{path}"
            # Try SKILL.md first, then README.md
            urls.append(f"{base}/SKILL.md")
            urls.append(f"{base}/README.md")
        return urls

    def _normalize_url(self, url: str) -> str:
        """Normalizuje podporované URL (GitHub blob -> raw, tree -> zkusí přímé soubory)."""
        value = (url or "").strip()
        if not value.startswith("http://") and not value.startswith("https://"):
            raise ValueError("invalid_url")

        # Handle GitHub blob URLs -> convert to raw
        if "github.com" in value and "/blob/" in value:
            value = value.replace("github.com", "raw.githubusercontent.com")
            value = value.replace("/blob/", "/")

        # Note: GitHub tree URLs are handled separately in install_skill
        # via _resolve_github_tree_urls()

        return value

    async def _fetch_bytes(self, url: str) -> bytes:
        """Stáhne bajty z URL s časovým limitem."""

        def _sync_fetch(target: str) -> bytes:
            with urllib.request.urlopen(
                target, timeout=self.valves.INSTALL_FETCH_TIMEOUT
            ) as resp:
                return resp.read()

        return await asyncio.wait_for(
            asyncio.to_thread(_sync_fetch, url),
            timeout=self.valves.INSTALL_FETCH_TIMEOUT + 1.0,
        )

    def _parse_skill_md_meta(
        self, content: str, fallback_name: str
    ) -> Tuple[str, str, str]:
        """Rozparsuje markdown obsah skillu na (název, popis, tělo)."""
        fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
        if fm_match:
            fm_text = fm_match.group(1)
            body = content[fm_match.end() :].strip()
            name = fallback_name
            description = ""
            for line in fm_text.split("\n"):
                m_name = re.match(r"^name:\s*(.+)$", line)
                if m_name:
                    name = m_name.group(1).strip().strip("\"'")
                m_desc = re.match(r"^description:\s*(.+)$", line)
                if m_desc:
                    description = m_desc.group(1).strip().strip("\"'")
            return name, description, body

        h1_match = re.search(r"^#\s+(.+)$", content.strip(), re.MULTILINE)
        name = h1_match.group(1).strip() if h1_match else fallback_name
        return name, "", content.strip()

    def _extract_skill_from_archive(self, payload: bytes) -> Tuple[str, str, str]:
        """Extract first SKILL.md (or README.md) from zip/tar archives."""
        with tempfile.TemporaryDirectory(prefix="owui-skill-") as tmp:
            root = Path(tmp)
            archive_path = root / "pkg"
            archive_path.write_bytes(payload)

            extract_dir = root / "extract"
            extract_dir.mkdir(parents=True, exist_ok=True)

            extracted = False
            try:
                with zipfile.ZipFile(archive_path, "r") as zf:
                    zf.extractall(extract_dir)
                    extracted = True
            except Exception:
                pass

            if not extracted:
                try:
                    with tarfile.open(archive_path, "r:*") as tf:
                        tf.extractall(extract_dir)
                        extracted = True
                except Exception:
                    pass

            if not extracted:
                raise ValueError("install_parse")

            candidates = list(extract_dir.rglob("SKILL.md"))
            if not candidates:
                candidates = list(extract_dir.rglob("README.md"))
            if not candidates:
                raise ValueError("install_parse")

            chosen = candidates[0]
            text = chosen.read_text(encoding="utf-8", errors="ignore")
            fallback_name = chosen.parent.name or "installed-skill"
            return self._parse_skill_md_meta(text, fallback_name)

    async def list_skills(
        self,
        include_content: bool = False,
        __user__: Optional[dict] = None,
        __event_emitter__: Optional[Any] = None,
        __event_call__: Optional[Any] = None,
        __request__: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Vypsat skills aktuálního uživatele v OpenWebUI."""
        user_ctx = await self._get_user_context(__user__, __event_call__, __request__)
        lang = user_ctx["user_language"]
        user_id = user_ctx["user_id"]

        try:
            self._require_skills_model()
            if not user_id:
                raise ValueError(self._t(lang, "err_user_required"))

            await self._emit_status(__event_emitter__, self._t(lang, "status_listing"))

            skills = self._user_skills(user_id, "read")
            rows = []
            for skill in skills:
                row = {
                    "id": str(getattr(skill, "id", "") or ""),
                    "name": getattr(skill, "name", ""),
                    "description": getattr(skill, "description", ""),
                    "is_active": bool(getattr(skill, "is_active", True)),
                    "updated_at": str(getattr(skill, "updated_at", "") or ""),
                }
                if include_content:
                    row["content"] = getattr(skill, "content", "")
                rows.append(row)

            rows.sort(key=lambda x: (x.get("name") or "").lower())
            active_count = sum(1 for row in rows if row.get("is_active"))

            await self._emit_status(
                __event_emitter__,
                self._t(
                    lang,
                    "status_list_done",
                    count=len(rows),
                    active_count=active_count,
                ),
                done=True,
            )
            return {"count": len(rows), "skills": rows}
        except Exception as e:
            msg = (
                self._t(lang, "err_unavailable")
                if str(e) == "skills_model_unavailable"
                else str(e)
            )
            await self._emit_status(__event_emitter__, msg, done=True)
            return {"error": msg}

    async def show_skill(
        self,
        skill_id: str = "",
        name: str = "",
        include_content: bool = True,
        __user__: Optional[dict] = None,
        __event_emitter__: Optional[Any] = None,
        __event_call__: Optional[Any] = None,
        __request__: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Show one skill by id or name."""
        user_ctx = await self._get_user_context(__user__, __event_call__, __request__)
        lang = user_ctx["user_language"]
        user_id = user_ctx["user_id"]

        try:
            self._require_skills_model()
            if not user_id:
                raise ValueError(self._t(lang, "err_user_required"))

            await self._emit_status(__event_emitter__, self._t(lang, "status_showing"))

            skill = self._find_skill(user_id=user_id, skill_id=skill_id, name=name)
            if not skill:
                raise ValueError(self._t(lang, "err_not_found"))

            result = {
                "id": str(getattr(skill, "id", "") or ""),
                "name": getattr(skill, "name", ""),
                "description": getattr(skill, "description", ""),
                "is_active": bool(getattr(skill, "is_active", True)),
                "updated_at": str(getattr(skill, "updated_at", "") or ""),
            }
            if include_content:
                result["content"] = getattr(skill, "content", "")

            skill_name = result.get("name") or result.get("id") or "unknown"
            await self._emit_status(
                __event_emitter__,
                self._t(lang, "status_show_done", name=skill_name),
                done=True,
            )
            return result
        except Exception as e:
            msg = (
                self._t(lang, "err_unavailable")
                if str(e) == "skills_model_unavailable"
                else str(e)
            )
            await self._emit_status(__event_emitter__, msg, done=True)
            return {"error": msg}

    async def _install_single_skill(
        self,
        url: str,
        name: str,
        user_id: str,
        lang: str,
        overwrite: bool,
        __event_emitter__: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Interní metoda pro instalaci jednoho skillu z URL."""
        try:
            if not (url or "").strip():
                raise ValueError(self._t(lang, "err_url_required"))

            # Extract potential folder name from URL before normalization
            url_folder = self._extract_folder_name_from_url(url).strip()

            parsed_name = ""
            parsed_desc = ""
            parsed_body = ""
            payload = None

            # Special handling for GitHub tree URLs
            if "github.com" in url and "/tree/" in url:
                fallback_file_urls = self._resolve_github_tree_urls(url)
                # Try to fetch SKILL.md or README.md directly from the tree path
                for file_url in fallback_file_urls:
                    try:
                        payload = await self._fetch_bytes(file_url)
                        if payload:
                            break
                    except Exception:
                        continue

                if payload:
                    # Successfully fetched direct file
                    text = payload.decode("utf-8", errors="ignore")
                    fallback = url_folder or "installed-skill"
                    parsed_name, parsed_desc, parsed_body = self._parse_skill_md_meta(
                        text, fallback
                    )
                else:
                    # Fallback: download entire branch as zip and extract
                    # This is a last resort if direct file access fails
                    raise ValueError(f"Could not find SKILL.md or README.md in {url}")
            else:
                # Handle other URL types (blob, direct markdown, archives)
                normalized = self._normalize_url(url)
                payload = await self._fetch_bytes(normalized)

                if normalized.lower().endswith((".zip", ".tar", ".tar.gz", ".tgz")):
                    parsed_name, parsed_desc, parsed_body = (
                        self._extract_skill_from_archive(payload)
                    )
                else:
                    text = payload.decode("utf-8", errors="ignore")
                    # Use extracted folder name as fallback
                    fallback = url_folder or "installed-skill"
                    parsed_name, parsed_desc, parsed_body = self._parse_skill_md_meta(
                        text, fallback
                    )

            final_name = (
                name or parsed_name or url_folder or "installed-skill"
            ).strip()
            final_desc = (parsed_desc or final_name).strip()
            final_content = (parsed_body or final_desc).strip()
            if not final_name:
                raise ValueError(self._t(lang, "err_name_required"))

            existing = self._find_skill(user_id=user_id, name=final_name)
            # install_skill always overwrites by default (overwrite=True);
            # ALLOW_OVERWRITE_ON_CREATE valve also controls this.
            allow_overwrite = overwrite or self.valves.ALLOW_OVERWRITE_ON_CREATE
            if existing:
                sid = str(getattr(existing, "id", "") or "")
                if not allow_overwrite:
                    # Should not normally reach here since install defaults overwrite=True
                    return {
                        "error": f"Skill already exists: {final_name}",
                        "hint": "Pass overwrite=true to replace the existing skill.",
                    }
                updated = Skills.update_skill_by_id(
                    sid,
                    {
                        "name": final_name,
                        "description": final_desc,
                        "content": final_content,
                        "is_active": True,
                    },
                )
                await self._emit_status(
                    __event_emitter__,
                    self._t(lang, "status_install_overwrite_done", name=final_name),
                    done=True,
                )
                return {
                    "success": True,
                    "action": "updated",
                    "id": str(getattr(updated, "id", "") or sid),
                    "name": final_name,
                    "source_url": url,
                }

            new_skill = Skills.insert_new_skill(
                user_id=user_id,
                form_data=SkillForm(
                    id=str(uuid.uuid4()),
                    name=final_name,
                    description=final_desc,
                    content=final_content,
                    meta=SkillMeta(),
                    is_active=True,
                ),
            )

            await self._emit_status(
                __event_emitter__,
                self._t(lang, "status_install_done", name=final_name),
                done=True,
            )
            return {
                "success": True,
                "action": "installed",
                "id": str(getattr(new_skill, "id", "") or ""),
                "name": final_name,
                "source_url": url,
            }
        except Exception as e:
            key = None
            if str(e) in {"invalid_url", "install_parse"}:
                key = (
                    "err_invalid_url"
                    if str(e) == "invalid_url"
                    else "err_install_parse"
                )
            msg = (
                self._t(lang, key)
                if key
                else (
                    self._t(lang, "err_unavailable")
                    if str(e) == "skills_model_unavailable"
                    else str(e)
                )
            )
            logger.error(
                f"_install_single_skill failed for {url}: {msg}", exc_info=True
            )
            return {"error": msg, "url": url}

    async def install_skill(
        self,
        url: str,
        name: str = "",
        overwrite: bool = True,
        __user__: Optional[dict] = None,
        __event_emitter__: Optional[Any] = None,
        __event_call__: Optional[Any] = None,
        __request__: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Nainstaluje jeden nebo více skills z URL, s podporou automatického objevení GitHub adresářů.

        Parametry:
            url: Jedna URL nebo JSON pole URL pro dávkovou instalaci.
                 Příklady:
                   Jedna: "https://github.com/owner/repo/tree/main/skills/xlsx"
                   Adresář: "https://github.com/owner/repo/tree/main/skills"
                   Dávka:  ["https://github.com/owner/repo/tree/main/skills/xlsx",
                            "https://github.com/owner/repo/tree/main/skills/csv"]
            name: Volitelný vlastní název skillu (pouze u jedné instalace).
            overwrite: Pokud True (výchozí), přepíše existující skill se stejným názvem.

        Automatické objevení:
        Pokud GitHub tree URL ukazuje na adresář s více podsložkami skills,
        nástroj automaticky objeví všechny a nainstaluje je dávkově.
        Příklad: "https://github.com/anthropics/skills/tree/main/skills" objeví
        všechny složky skills a nainstaluje je najednou.

        Podporované formáty URL:
        - GitHub tree: https://github.com/owner/repo/tree/branch/cesta/k/skillu
        - GitHub adresář skills (auto-discovery): https://github.com/owner/repo/tree/branch/cesta
        - GitHub blob: https://github.com/owner/repo/blob/branch/cesta/SKILL.md
        - Raw markdown: https://raw.githubusercontent.com/.../SKILL.md
        - Archiv: https://example.com/skill.zip (musí obsahovat SKILL.md nebo README.md)
        """
        user_ctx = await self._get_user_context(__user__, __event_call__, __request__)
        lang = user_ctx["user_language"]
        user_id = user_ctx["user_id"]

        try:
            self._require_skills_model()
            if not user_id:
                raise ValueError(self._t(lang, "err_user_required"))

            # Stage 1: Check for directory auto-discovery (single string GitHub URL)
            if isinstance(url, str) and "github.com" in url and "/tree/" in url:
                await self._emit_status(
                    __event_emitter__,
                    self._t(lang, "status_discovering_skills", url=(url or "")[-50:]),
                )
                discover_fn = getattr(
                    self, "_discover_skills_from_github_directory", None
                )
                discovered = []
                if callable(discover_fn):
                    discovered = await discover_fn(url, lang)
                else:
                    logger.warning(
                        "_discover_skills_from_github_directory is unavailable on current Tools instance."
                    )
                if discovered:
                    # Auto-discovered subdirectories, treat as batch
                    url = discovered

            # Stage 2: Check if url is a list/tuple (batch mode)
            if isinstance(url, (list, tuple)):
                urls = url
                if not urls:
                    raise ValueError(self._t(lang, "err_url_required"))

                await self._emit_status(
                    __event_emitter__,
                    self._t(lang, "status_installing_batch", total=len(urls)),
                )

                results = []
                for idx, single_url in enumerate(urls, 1):
                    result = await self._install_single_skill(
                        url=str(single_url).strip(),
                        name="",  # Batch mode doesn't support per-item names
                        user_id=user_id,
                        lang=lang,
                        overwrite=overwrite,
                        __event_emitter__=__event_emitter__,
                    )
                    results.append(result)

                # Summary
                success_count = sum(1 for r in results if r.get("success"))
                error_count = len(results) - success_count

                await self._emit_status(
                    __event_emitter__,
                    self._t(
                        lang,
                        "status_install_batch_done",
                        succeeded=success_count,
                        failed=error_count,
                    ),
                    done=True,
                )

                return {
                    "batch": True,
                    "total": len(results),
                    "succeeded": success_count,
                    "failed": error_count,
                    "results": results,
                }
            else:
                # Single mode
                if not (url or "").strip():
                    raise ValueError(self._t(lang, "err_url_required"))

                await self._emit_status(
                    __event_emitter__, self._t(lang, "status_installing")
                )

                result = await self._install_single_skill(
                    url=str(url).strip(),
                    name=name,
                    user_id=user_id,
                    lang=lang,
                    overwrite=overwrite,
                    __event_emitter__=__event_emitter__,
                )
                return result

        except Exception as e:
            key = None
            if str(e) in {"invalid_url", "install_parse"}:
                key = (
                    "err_invalid_url"
                    if str(e) == "invalid_url"
                    else "err_install_parse"
                )
            msg = (
                self._t(lang, key)
                if key
                else (
                    self._t(lang, "err_unavailable")
                    if str(e) == "skills_model_unavailable"
                    else str(e)
                )
            )
            await self._emit_status(__event_emitter__, msg, done=True)
            logger.error(f"install_skill failed: {msg}", exc_info=True)
            return {"error": msg}

    async def create_skill(
        self,
        name: str,
        description: str = "",
        content: str = "",
        overwrite: bool = False,
        __user__: Optional[dict] = None,
        __event_emitter__: Optional[Any] = None,
        __event_call__: Optional[Any] = None,
        __request__: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Vytvoří nový skill, nebo aktualizuje skill se stejným názvem při zapnutém overwrite."""
        user_ctx = await self._get_user_context(__user__, __event_call__, __request__)
        lang = user_ctx["user_language"]
        user_id = user_ctx["user_id"]

        try:
            self._require_skills_model()
            if not user_id:
                raise ValueError(self._t(lang, "err_user_required"))

            skill_name = (name or "").strip()
            if not skill_name:
                raise ValueError(self._t(lang, "err_name_required"))

            await self._emit_status(__event_emitter__, self._t(lang, "status_creating"))

            existing = self._find_skill(user_id=user_id, name=skill_name)
            allow_overwrite = overwrite or self.valves.ALLOW_OVERWRITE_ON_CREATE

            final_description = (description or skill_name).strip()
            final_content = (content or final_description).strip()

            if existing:
                if not allow_overwrite:
                    return {
                        "error": f"Skill already exists: {skill_name}",
                        "hint": "Use overwrite=true to update existing skill.",
                    }

                sid = str(getattr(existing, "id", "") or "")
                updated = Skills.update_skill_by_id(
                    sid,
                    {
                        "name": skill_name,
                        "description": final_description,
                        "content": final_content,
                        "is_active": True,
                    },
                )
                await self._emit_status(
                    __event_emitter__,
                    self._t(lang, "status_create_overwrite_done", name=skill_name),
                    done=True,
                )
                return {
                    "success": True,
                    "action": "updated",
                    "id": str(getattr(updated, "id", "") or sid),
                    "name": skill_name,
                }

            new_skill = Skills.insert_new_skill(
                user_id=user_id,
                form_data=SkillForm(
                    id=str(uuid.uuid4()),
                    name=skill_name,
                    description=final_description,
                    content=final_content,
                    meta=SkillMeta(),
                    is_active=True,
                ),
            )

            await self._emit_status(
                __event_emitter__,
                self._t(lang, "status_create_done", name=skill_name),
                done=True,
            )
            return {
                "success": True,
                "action": "created",
                "id": str(getattr(new_skill, "id", "") or ""),
                "name": skill_name,
            }
        except Exception as e:
            msg = (
                self._t(lang, "err_unavailable")
                if str(e) == "skills_model_unavailable"
                else str(e)
            )
            await self._emit_status(__event_emitter__, msg, done=True)
            logger.error(f"create_skill failed: {msg}", exc_info=True)
            return {"error": msg}

    async def update_skill(
        self,
        skill_id: str = "",
        name: str = "",
        new_name: str = "",
        description: str = "",
        content: str = "",
        is_active: Optional[bool] = None,
        __user__: Optional[dict] = None,
        __event_emitter__: Optional[Any] = None,
        __event_call__: Optional[Any] = None,
        __request__: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Aktualizuje pole jednoho skillu podle id nebo názvu."""
        user_ctx = await self._get_user_context(__user__, __event_call__, __request__)
        lang = user_ctx["user_language"]
        user_id = user_ctx["user_id"]

        try:
            self._require_skills_model()
            if not user_id:
                raise ValueError(self._t(lang, "err_user_required"))

            await self._emit_status(__event_emitter__, self._t(lang, "status_updating"))

            skill = self._find_skill(user_id=user_id, skill_id=skill_id, name=name)
            if not skill:
                raise ValueError(self._t(lang, "err_not_found"))

            updates: Dict[str, Any] = {}
            if new_name.strip():
                updates["name"] = new_name.strip()
            if description.strip():
                updates["description"] = description.strip()
            if content.strip():
                updates["content"] = content.strip()
            if is_active is not None:
                updates["is_active"] = bool(is_active)

            if not updates:
                raise ValueError(self._t(lang, "err_no_update_fields"))

            sid = str(getattr(skill, "id", "") or "")
            updated = Skills.update_skill_by_id(sid, updates)
            updated_name = str(
                getattr(updated, "name", "")
                or updates.get("name")
                or getattr(skill, "name", "")
                or sid
            )

            await self._emit_status(
                __event_emitter__,
                self._t(lang, "status_update_done", name=updated_name),
                done=True,
            )
            return {
                "success": True,
                "id": str(getattr(updated, "id", "") or sid),
                "name": str(
                    getattr(updated, "name", "")
                    or updates.get("name")
                    or getattr(skill, "name", "")
                ),
                "updated_fields": list(updates.keys()),
            }
        except Exception as e:
            msg = (
                self._t(lang, "err_unavailable")
                if str(e) == "skills_model_unavailable"
                else str(e)
            )
            await self._emit_status(__event_emitter__, msg, done=True)
            return {"error": msg}

    async def delete_skill(
        self,
        skill_id: str = "",
        name: str = "",
        __user__: Optional[dict] = None,
        __event_emitter__: Optional[Any] = None,
        __event_call__: Optional[Any] = None,
        __request__: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Smaže jeden skill podle id nebo názvu."""
        user_ctx = await self._get_user_context(__user__, __event_call__, __request__)
        lang = user_ctx["user_language"]
        user_id = user_ctx["user_id"]

        try:
            self._require_skills_model()
            if not user_id:
                raise ValueError(self._t(lang, "err_user_required"))

            await self._emit_status(__event_emitter__, self._t(lang, "status_deleting"))

            skill = self._find_skill(user_id=user_id, skill_id=skill_id, name=name)
            if not skill:
                raise ValueError(self._t(lang, "err_not_found"))

            sid = str(getattr(skill, "id", "") or "")
            sname = str(getattr(skill, "name", "") or "")
            Skills.delete_skill_by_id(sid)
            deleted_name = sname or sid or "unknown"

            await self._emit_status(
                __event_emitter__,
                self._t(lang, "status_delete_done", name=deleted_name),
                done=True,
            )
            return {
                "success": True,
                "id": sid,
                "name": sname,
            }
        except Exception as e:
            msg = (
                self._t(lang, "err_unavailable")
                if str(e) == "skills_model_unavailable"
                else str(e)
            )
            await self._emit_status(__event_emitter__, msg, done=True)
            return {"error": msg}
