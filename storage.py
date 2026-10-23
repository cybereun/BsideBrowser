# -*- coding: utf-8 -*-
"""
Bside Browser & AI Agent — Persistent Storage Manager
Manages Sessions, Messages, Bookmarks, History, Memories, Projects, Routines, Skills, and Vault (Logins & Cards).
"""

import os
import json
import uuid
import time
from typing import Dict, List, Any, Optional


DEFAULT_SKILLS = [
    {
        "id": "bside",
        "name": "Bside Browser Control",
        "tag": "@bside",
        "category": "Browser",
        "description": "탭 열기/닫기/전환, 북마크 및 방문 기록 조회를 수행하는 브라우저 내장 제어 스킬",
        "enabled": True,
    },
    {
        "id": "bsidewright",
        "name": "Bsidewright (DOM Automation)",
        "tag": "@bsidewright",
        "category": "Automation",
        "description": "현재 활성 웹페이지의 DOM 스냅샷 추출, 버튼 클릭, 입력란 작성, 스크롤 등 자율 웹 조작",
        "enabled": True,
    },
    {
        "id": "visual-browse",
        "name": "Visual Browse",
        "tag": "@visual-browse",
        "category": "Vision",
        "description": "활성 탭의 화면을 캡처하고 시각적 레이아웃과 핵심 요소를 분석하는 스킬",
        "enabled": True,
    },
    {
        "id": "visualize",
        "name": "Interactive Visualizer",
        "tag": "@visualize",
        "category": "Canvas",
        "description": "응답 내에 인터랙티브 SVG/HTML 차트, 아키텍처 다이어그램, 데이터 대시보드를 렌더링",
        "enabled": True,
    },
    {
        "id": "draft-preview",
        "name": "Draft Preview (Email / Slack / SNS)",
        "tag": "@draft-preview",
        "category": "Productivity",
        "description": "Gmail, Slack, X(Twitter), LinkedIn 초안 카드를 생성하고 즉시 복사/전송 준비",
        "enabled": True,
    },
    {
        "id": "doc-export",
        "name": "Document Synthesizer",
        "tag": "@doc",
        "category": "Document",
        "description": "웹 리서치 결과나 페이지 요약을 구조화된 마크다운/HTML 보고서로 생성",
        "enabled": True,
    },
]

DEFAULT_BOOKMARKS = [
    {"id": "bm_1", "title": "Bside 새 탭", "url": "bside://newtab", "icon": "✦"},
    {"id": "bm_2", "title": "Bside 워크스페이스", "url": "bside://workspace", "icon": "❖"},
    {"id": "bm_3", "title": "Google", "url": "https://www.google.com", "icon": "G"},
    {"id": "bm_4", "title": "Naver", "url": "https://www.naver.com", "icon": "N"},
    {"id": "bm_5", "title": "GitHub", "url": "https://github.com", "icon": "🐙"},
    {"id": "bm_6", "title": "Hacker News", "url": "https://news.ycombinator.com", "icon": "Y"},
    {"id": "bm_7", "title": "Wikipedia", "url": "https://ko.wikipedia.org", "icon": "W"},
]

DEFAULT_PROJECTS = [
    {
        "id": "proj_default",
        "name": "웹 리서치 & 자동화",
        "description": "활성 탭 분석, 경쟁사 조사 및 핵심 데이터 시각화 워크스페이스",
        "instructions": "항상 한국어로 명확하게 핵심을 요약하고, 수치가 있으면 @visualize 차트를 함께 제공하세요.",
        "created_at": int(time.time()),
    },
    {
        "id": "proj_dev",
        "name": "리버스 엔지니어링 & 아키텍처",
        "description": "앱 구조 분석, 코드 리뷰 및 기술 문서 작성 프로젝트",
        "instructions": "근거(Evidence)와 추론을 명확히 구분하고 다이어그램으로 아키텍처를 설명하세요.",
        "created_at": int(time.time()),
    },
]

DEFAULT_ROUTINES = [
    {
        "id": "rt_morning",
        "name": "현재 페이지 핵심 브리핑 & 차트 요약",
        "schedule": "수동 실행 / 매일 09:00",
        "prompt": "현재 열린 웹페이지의 핵심 내용을 분석해서 3줄 요약과 주요 키워드 비중 차트(@visualize)를 만들어줘.",
        "enabled": True,
    },
    {
        "id": "rt_links",
        "name": "페이지 내 주요 링크 & 액션 아이템 추출",
        "schedule": "수동 실행 / 온디맨드",
        "prompt": "현재 탭의 DOM 요소를 스캔해서 주요 링크와 클릭 가능한 핵심 버튼들을 표로 정리해줘.",
        "enabled": True,
    },
    {
        "id": "rt_email",
        "name": "현재 아티클 공유 이메일 초안 작성",
        "schedule": "수동 실행 / 온디맨드",
        "prompt": "현재 보고 있는 웹페이지 내용을 팀원들에게 공유하기 위한 요약 이메일 초안(@draft-preview)을 작성해줘.",
        "enabled": True,
    },
]

DEFAULT_MEMORIES = [
    {
        "id": "mem_1",
        "content": "사용자는 모든 AI 응답과 요약 리포트를 한국어로 제공받기를 선호함.",
        "source": "User Preference",
        "created_at": int(time.time()),
    },
    {
        "id": "mem_2",
        "content": "복잡한 아키텍처나 통계 데이터 설명 시 인라인 SVG/HTML 시각화 카드를 포함하는 것을 선호함.",
        "source": "Bside Memory Engine",
        "created_at": int(time.time()),
    },
]


class StorageManager:
    def __init__(self, data_dir: Optional[str] = None):
        if data_dir is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            data_dir = os.path.join(base_dir, "user_data")
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)
        self.state_file = os.path.join(self.data_dir, "bside_state.json")
        self.data: Dict[str, Any] = self._load()

    def _default_state(self) -> Dict[str, Any]:
        welcome_session_id = "sess_welcome"
        now = int(time.time())
        return {
            "settings": {
                "theme": "light",
                "search_engine": "https://www.google.com/search?q=",
                "default_model": "codex:GPT-6 Luna",
                "selected_sub_model_name": "GPT-6 Luna",
                "reasoning_effort": "Extra High",
                "fast_mode": True,
                "vault_auto_fill": True,
                "permission_mode": "auto-safe",
                "sidebar_open": True,
                "sidebar_width": 410,
                "openai_api_key": os.environ.get("OPENAI_API_KEY", ""),
                "anthropic_api_key": os.environ.get("ANTHROPIC_API_KEY", ""),
                "gemini_api_key": os.environ.get("GEMINI_API_KEY", ""),
                "custom_base_url": "http://localhost:11434/v1",
                "custom_model_name": "qwen2.5:7b",
            },
            "bookmarks": DEFAULT_BOOKMARKS,
            "history": [],
            "projects": DEFAULT_PROJECTS,
            "routines": DEFAULT_ROUTINES,
            "memories": DEFAULT_MEMORIES,
            "skills": DEFAULT_SKILLS,
            "vault": [
                {
                    "id": "v_1",
                    "type": "login",
                    "site": "https://github.com",
                    "title": "GitHub Developer Account",
                    "username": "bside-user@studio.at",
                    "password": "bside-demo-password",
                    "updated_at": now,
                }
            ],
            "vault_cards": [],
            "sessions": [
                {
                    "id": welcome_session_id,
                    "title": "Bside 브라우저 & AI 에이전트 시작하기",
                    "project_id": "proj_default",
                    "created_at": now,
                    "updated_at": now,
                    "messages": [
                        {
                            "id": "msg_welcome_1",
                            "role": "assistant",
                            "timestamp": now,
                            "steps": [
                                {
                                    "tool": "BsideAgentManager",
                                    "status": "done",
                                    "summary": "Bside v1.0.1022.1 사이드바 및 Bsidewright 브릿지 초기화 완료",
                                }
                            ],
                            "content": (
                                "안녕하세요! **Bside 브라우저 & AI 에이전트 사이드바**에 오신 것을 환영합니다.\n\n"
                                "오른쪽 사이드바(`Alt+Shift+B`)와 주소창/새 탭의 **듀얼 모드 옴니박스(`Tab` 키로 Search ↔ Ask 전환)**에서 언제든 AI 에이전트를 호출할 수 있습니다.\n\n"
                                "### 주요 기능 바로 써보기\n"
                                "- **현재 페이지 분석 & 요약**: `현재 페이지 요약해줘` 또는 `@tabs 열린 탭 모두 비교해줘`\n"
                                "- **자율 웹 조작 (Bsidewright)**: `검색창에 인공지능 입력하고 클릭해줘`, `아래로 스크롤해줘`, `네이버 열어줘`\n"
                                "- **Bside Vault 자동 로그인/결제**: 상단 열쇠 아이콘(🔑)에 아이디/비밀번호나 카드번호를 저장하면 페이지 접속 시 자동 입력하거나 `'로그인해줘'`, `'카드 자동입력해줘'`로 즉시 동작합니다."
                            ),
                        }
                    ],
                }
            ],
            "active_session_id": welcome_session_id,
        }

    def _load(self) -> Dict[str, Any]:
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                default = self._default_state()
                for k, v in default.items():
                    if k not in loaded:
                        loaded[k] = v
                for sk, sv in default["settings"].items():
                    if sk not in loaded["settings"]:
                        loaded["settings"][sk] = sv
                return loaded
            except Exception:
                pass
        state = self._default_state()
        self._save_raw(state)
        return state

    def _save_raw(self, state: Dict[str, Any]) -> None:
        try:
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def save(self) -> None:
        self._save_raw(self.data)

    # --- Settings ---
    def get_setting(self, key: str, default: Any = None) -> Any:
        return self.data.get("settings", {}).get(key, default)

    def set_setting(self, key: str, value: Any) -> None:
        self.data.setdefault("settings", {})[key] = value
        self.save()

    def update_settings(self, updates: Dict[str, Any]) -> None:
        self.data.setdefault("settings", {}).update(updates)
        self.save()

    # --- Sessions & Messages ---
    def get_sessions(self) -> List[Dict[str, Any]]:
        sessions = self.data.get("sessions", [])
        return sorted(sessions, key=lambda s: s.get("updated_at", 0), reverse=True)

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        for s in self.data.get("sessions", []):
            if s.get("id") == session_id:
                return s
        return None

    def get_active_session(self) -> Dict[str, Any]:
        active_id = self.data.get("active_session_id")
        if active_id:
            s = self.get_session(active_id)
            if s:
                return s
        sessions = self.get_sessions()
        if sessions:
            self.data["active_session_id"] = sessions[0]["id"]
            return sessions[0]
        return self.create_session("새 에이전트 세션")

    def create_session(self, title: str = "새 에이전트 세션", project_id: str = "proj_default") -> Dict[str, Any]:
        now = int(time.time())
        sess = {
            "id": f"sess_{uuid.uuid4().hex[:10]}",
            "title": title,
            "project_id": project_id,
            "created_at": now,
            "updated_at": now,
            "messages": [],
        }
        self.data.setdefault("sessions", []).insert(0, sess)
        self.data["active_session_id"] = sess["id"]
        self.save()
        return sess

    def delete_session(self, session_id: str) -> None:
        sessions = [s for s in self.data.get("sessions", []) if s.get("id") != session_id]
        self.data["sessions"] = sessions
        if self.data.get("active_session_id") == session_id:
            self.data["active_session_id"] = sessions[0]["id"] if sessions else None
        if not self.data["sessions"]:
            self.create_session("새 에이전트 세션")
        else:
            self.save()

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        steps: Optional[List[Dict[str, Any]]] = None,
        visual_html: Optional[str] = None,
        draft_card: Optional[Dict[str, Any]] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        sess = self.get_session(session_id)
        if not sess:
            sess = self.create_session()
        now = int(time.time())
        msg = {
            "id": f"msg_{uuid.uuid4().hex[:10]}",
            "role": role,
            "content": content,
            "timestamp": now,
            "steps": steps or [],
            "visual_html": visual_html or "",
            "draft_card": draft_card or None,
            "attachments": attachments or [],
        }
        sess.setdefault("messages", []).append(msg)
        sess["updated_at"] = now
        if role == "user" and (sess.get("title") in ("새 에이전트 세션", "New Session", "새 대화") or len(sess["messages"]) == 1):
            clean = content.strip().replace("\n", " ")
            sess["title"] = clean[:36] + ("…" if len(clean) > 36 else "")
        self.save()
        return msg

    # --- Bookmarks & History ---
    def get_bookmarks(self) -> List[Dict[str, Any]]:
        return self.data.get("bookmarks", [])

    def add_bookmark(self, title: str, url: str, icon: str = "★") -> Dict[str, Any]:
        for bm in self.data.get("bookmarks", []):
            if bm.get("url") == url:
                return bm
        bm = {
            "id": f"bm_{uuid.uuid4().hex[:8]}",
            "title": title or url,
            "url": url,
            "icon": icon,
        }
        self.data.setdefault("bookmarks", []).append(bm)
        self.save()
        return bm

    def remove_bookmark(self, url_or_id: str) -> None:
        self.data["bookmarks"] = [
            b for b in self.data.get("bookmarks", [])
            if b.get("url") != url_or_id and b.get("id") != url_or_id
        ]
        self.save()

    def is_bookmarked(self, url: str) -> bool:
        return any(b.get("url") == url for b in self.data.get("bookmarks", []))

    def add_history(self, title: str, url: str) -> None:
        if not url or url.startswith("data:"):
            return
        now = int(time.time())
        hist = self.data.setdefault("history", [])
        if hist and hist[0].get("url") == url:
            hist[0]["title"] = title or url
            hist[0]["timestamp"] = now
        else:
            hist.insert(
                0,
                {
                    "id": f"h_{uuid.uuid4().hex[:8]}",
                    "title": title or url,
                    "url": url,
                    "timestamp": now,
                },
            )
        self.data["history"] = hist[:250]
        self.save()

    def get_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        return self.data.get("history", [])[:limit]

    # --- Memories, Projects, Routines, Vault (Logins & Payment Cards) ---
    def add_memory(self, content: str, source: str = "User") -> Dict[str, Any]:
        mem = {
            "id": f"mem_{uuid.uuid4().hex[:8]}",
            "content": content.strip(),
            "source": source,
            "created_at": int(time.time()),
        }
        self.data.setdefault("memories", []).insert(0, mem)
        self.save()
        return mem

    def delete_memory(self, mem_id: str) -> None:
        self.data["memories"] = [m for m in self.data.get("memories", []) if m.get("id") != mem_id]
        self.save()

    def add_project(self, name: str, description: str, instructions: str = "") -> Dict[str, Any]:
        proj = {
            "id": f"proj_{uuid.uuid4().hex[:8]}",
            "name": name.strip(),
            "description": description.strip(),
            "instructions": instructions.strip(),
            "created_at": int(time.time()),
        }
        self.data.setdefault("projects", []).insert(0, proj)
        self.save()
        return proj

    def add_routine(self, name: str, schedule: str, prompt: str) -> Dict[str, Any]:
        rt = {
            "id": f"rt_{uuid.uuid4().hex[:8]}",
            "name": name.strip(),
            "schedule": schedule.strip() or "수동 실행",
            "prompt": prompt.strip(),
            "enabled": True,
        }
        self.data.setdefault("routines", []).insert(0, rt)
        self.save()
        return rt

    def add_vault_entry(self, site: str, title: str, username: str, password: str) -> Dict[str, Any]:
        entry = {
            "id": f"v_{uuid.uuid4().hex[:8]}",
            "type": "login",
            "site": site.strip(),
            "title": title.strip() or site.strip(),
            "username": username.strip(),
            "password": password,
            "updated_at": int(time.time()),
        }
        self.data.setdefault("vault", []).insert(0, entry)
        self.save()
        return entry

    def delete_vault_entry(self, entry_id: str) -> None:
        self.data["vault"] = [v for v in self.data.get("vault", []) if v.get("id") != entry_id]
        self.save()

    def find_vault_entry_for_url(self, current_url: str) -> Optional[Dict[str, Any]]:
        """Matches a saved login credential by domain/host against the current page URL."""
        if not current_url or current_url.startswith("bside://"):
            return None
        import urllib.parse
        cur_host = (urllib.parse.urlparse(current_url).netloc or "").lower().replace("www.", "")
        if not cur_host:
            return None
        for v in self.data.get("vault", []):
            site_raw = (v.get("site") or "").strip()
            if "://" not in site_raw:
                site_host = site_raw.lower().replace("www.", "").split("/")[0]
            else:
                site_host = (urllib.parse.urlparse(site_raw).netloc or "").lower().replace("www.", "")
            if site_host and (site_host in cur_host or cur_host in site_host):
                return v
        return None

    def add_card_entry(
        self,
        label: str,
        cardholder: str,
        number: str,
        expiry: str,
        cvc: str,
    ) -> Dict[str, Any]:
        card = {
            "id": f"card_{uuid.uuid4().hex[:8]}",
            "type": "card",
            "label": label.strip() or "내 결제 카드",
            "cardholder": cardholder.strip(),
            "number": number.strip(),
            "expiry": expiry.strip(),
            "cvc": cvc.strip(),
            "updated_at": int(time.time()),
        }
        self.data.setdefault("vault_cards", []).insert(0, card)
        self.save()
        return card

    def get_card_entries(self) -> List[Dict[str, Any]]:
        return self.data.get("vault_cards", [])

    def delete_card_entry(self, card_id: str) -> None:
        self.data["vault_cards"] = [c for c in self.data.get("vault_cards", []) if c.get("id") != card_id]
        self.save()
