# -*- coding: utf-8 -*-
"""
Bside Browser & AI Agent — Autonomous Agent Engine, Remote Page Controller & Fast Streaming
Supports explicit manual selection between:
1. Subscription CLI Models (No unexpected API charges; emits a popup alert if subscription quota/tokens are exhausted):
   - `claude-sub`: Claude Code Subscription (`claude.cmd`)
   - `codex-sub`: OpenAI Codex Subscription (`codex.cmd`)
   - `antigravity-sub`: Antigravity CLI Subscription (`agy.exe`)
2. Direct API Key Models (Used only when explicitly selected by the user):
   - `claude-api`: Anthropic API (`claude-3-5-sonnet-latest`)
   - `openai-api`: OpenAI API (`gpt-4o-mini`)
   - `gemini-api`: Google Gemini API (`gemini-2.5-flash`)
   - `custom-local`: Local Ollama / OpenAI-compatible server
3. Built-in Bside DOM Engine:
   - `bside-autonomous-v1`: Instant offline DOM analyzer & remote controller
"""

import os
import json
import re
import shutil
import subprocess
import tempfile
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional, Tuple
from PySide6.QtCore import QThread, Signal


def get_subscription_auth_status() -> Dict[str, Dict[str, Any]]:
    """Checks local CLI installation and OAuth/subscription login status for Claude, Codex, and Antigravity."""
    home = os.path.expanduser("~")
    npm_dir = os.path.join(os.environ.get("APPDATA", ""), "npm")
    local_appdata = os.environ.get("LOCALAPPDATA", "")

    # 1. Claude Code CLI
    claude_bin = os.path.join(npm_dir, "claude.cmd")
    if not os.path.exists(claude_bin):
        claude_bin = shutil.which("claude.cmd") or shutil.which("claude") or ""
    claude_cred = os.path.join(home, ".claude", ".credentials.json")
    claude_logged_in = os.path.exists(claude_cred) and os.path.getsize(claude_cred) > 10

    # 2. Codex CLI
    codex_bin = os.path.join(npm_dir, "codex.cmd")
    if not os.path.exists(codex_bin):
        codex_bin = shutil.which("codex.cmd") or shutil.which("codex") or ""
    codex_cred = os.path.join(home, ".codex", "auth.json")
    codex_logged_in = os.path.exists(codex_cred) and os.path.getsize(codex_cred) > 10

    # 3. Antigravity CLI (agy.exe)
    agy_bin = os.path.join(local_appdata, "agy", "bin", "agy.exe")
    if not os.path.exists(agy_bin):
        agy_bin = shutil.which("agy.exe") or shutil.which("agy") or ""
    agy_state = os.path.join(home, ".gemini", "antigravity-cli", "jetski_state.pbtxt")
    agy_google = os.path.join(home, ".gemini", "google_accounts.json")
    agy_logged_in = os.path.exists(agy_state) or os.path.exists(agy_google)

    # 4. Gemini CLI (gemini.cmd)
    gemini_bin = os.path.join(npm_dir, "gemini.cmd")
    if not os.path.exists(gemini_bin):
        gemini_bin = shutil.which("gemini.cmd") or shutil.which("gemini") or ""
    gemini_logged_in = os.path.exists(agy_google)

    return {
        "claude": {
            "name": "Claude 구독 (Claude Code CLI)",
            "bin": claude_bin,
            "installed": bool(claude_bin),
            "logged_in": claude_logged_in,
            "cred_path": claude_cred,
            "login_cmd": f'"{claude_bin or "claude"}"',
        },
        "codex": {
            "name": "Codex 구독 (ChatGPT/Codex CLI)",
            "bin": codex_bin,
            "installed": bool(codex_bin),
            "logged_in": codex_logged_in,
            "cred_path": codex_cred,
            "login_cmd": f'"{codex_bin or "codex"}" login',
        },
        "antigravity": {
            "name": "Antigravity 구독 (agy.exe CLI)",
            "bin": agy_bin,
            "installed": bool(agy_bin),
            "logged_in": agy_logged_in,
            "cred_path": agy_state,
            "login_cmd": f'"{agy_bin or "agy"}"',
        },
        "gemini": {
            "name": "Gemini CLI 구독 (gemini.cmd)",
            "bin": gemini_bin,
            "installed": bool(gemini_bin),
            "logged_in": gemini_logged_in,
            "cred_path": agy_google,
            "login_cmd": f'"{gemini_bin or "gemini"}"',
        },
    }


def launch_subscription_login_terminal(provider: str) -> Tuple[bool, str]:
    """
    Opens an interactive Windows command window running the official CLI login flow
    so the browser OAuth login window pops up immediately.
    """
    status = get_subscription_auth_status()
    info = status.get(provider)
    if not info or not info.get("installed"):
        return False, f"{provider} CLI가 설치되어 있지 않습니다."

    bin_path = info["bin"]
    if provider == "codex":
        cmdline = f'start "Bside - Codex Subscription Login" cmd /k ""{bin_path}" login"'
    elif provider == "claude":
        cmdline = f'start "Bside - Claude Subscription Login" cmd /k ""{bin_path}""'
    elif provider == "antigravity":
        cmdline = f'start "Bside - Antigravity CLI Login" cmd /k ""{bin_path}""'
    else:
        cmdline = f'start "Bside - Gemini CLI Login" cmd /k ""{bin_path}""'

    try:
        subprocess.Popen(cmdline, shell=True)
        return True, f"{info['name']} 로그인/인증 창을 실행했습니다. 브라우저 OAuth 로그인을 완료해 주세요."
    except Exception as e:
        return False, str(e)


BSIDEWRIGHT_SNAPSHOT_JS = """
(() => {
    try {
        const title = document.title || '';
        const url = window.location.href || '';
        const metaDesc = document.querySelector('meta[name="description"]')?.content || '';

        const headings = Array.from(document.querySelectorAll('h1, h2, h3'))
            .map(h => ({ tag: h.tagName, text: (h.innerText || '').trim().slice(0, 120) }))
            .filter(h => h.text.length > 0)
            .slice(0, 18);

        const interactives = [];
        const els = document.querySelectorAll('a[href], button, input, textarea, select, [role="button"], [contenteditable="true"]');
        let idx = 1;
        for (const el of els) {
            const rect = el.getBoundingClientRect();
            if (rect.width === 0 || rect.height === 0) continue;
            const label = (
                el.innerText ||
                el.getAttribute('aria-label') ||
                el.getAttribute('placeholder') ||
                el.value ||
                el.getAttribute('title') ||
                el.getAttribute('name') ||
                ''
            ).trim().replace(/\\s+/g, ' ').slice(0, 80);
            const tag = el.tagName.toLowerCase();
            const type = el.getAttribute('type') || '';
            const href = el.getAttribute('href') || '';
            if (!label && tag !== 'input' && tag !== 'textarea' && !el.isContentEditable) continue;
            el.setAttribute('data-bside-id', String(idx));
            interactives.push({
                id: idx,
                tag,
                type,
                label: label || `[${tag} ${type}]`,
                href: href.slice(0, 100)
            });
            idx++;
            if (idx > 40) break;
        }

        const bodyText = (document.body ? document.body.innerText : '')
            .replace(/\\s+/g, ' ')
            .trim()
            .slice(0, 3200);

        return {
            title,
            url,
            metaDesc,
            headings,
            interactives,
            bodyText
        };
    } catch (e) {
        return {
            title: document.title || '',
            url: window.location.href || '',
            metaDesc: '',
            headings: [],
            interactives: [],
            bodyText: String(e)
        };
    }
})();
"""


def build_bsidewright_action_js(action: Dict[str, Any]) -> str:
    """
    Builds JS to execute a Bsidewright remote page action on the active web page
    AND shows a sleek floating AI Remote Badge on the web page so the user can visually
    see the AI controlling the page in real time.
    """
    act_type = action.get("action", "")
    target = action.get("target", "")
    value = action.get("value", "")

    target_json = json.dumps(str(target), ensure_ascii=False)
    value_json = json.dumps(str(value), ensure_ascii=False)

    toast_helper = """
    const showAiRemoteToast = (msg) => {
        let badge = document.getElementById('bside-ai-remote-toast');
        if (!badge) {
            badge = document.createElement('div');
            badge.id = 'bside-ai-remote-toast';
            badge.style.cssText = 'position:fixed;bottom:24px;right:24px;z-index:2147483647;background:rgba(28,28,32,0.92);color:#fff;padding:10px 16px;border-radius:14px;font-family:sans-serif;font-size:13px;font-weight:600;box-shadow:0 8px 24px rgba(0,0,0,0.25);border:1px solid rgba(255,255,255,0.15);transition:opacity 0.3s;';
            document.body.appendChild(badge);
        }
        badge.innerText = '✦ Bside AI 원격 제어: ' + msg;
        badge.style.opacity = '1';
        setTimeout(() => { if (badge) badge.style.opacity = '0'; }, 2600);
    };
    """

    if act_type == "scroll":
        direction = str(value or target or "down").lower()
        delta = -600 if ("up" in direction or "위" in direction) else 600
        return f"""
        (() => {{
            {toast_helper}
            window.scrollBy({{ top: {delta}, behavior: 'smooth' }});
            showAiRemoteToast('화면 스크롤 ({direction})');
            return 'Scrolled {direction}';
        }})();
        """

    if act_type == "click":
        return f"""
        (() => {{
            {toast_helper}
            const query = {target_json}.toLowerCase().replace(/^#/, '');
            let el = document.querySelector(`[data-bside-id="${{query}}"]`);
            if (!el) {{
                try {{ el = document.querySelector({target_json}); }} catch(e) {{}}
            }}
            if (!el) {{
                const candidates = Array.from(document.querySelectorAll('a, button, input[type="submit"], input[type="button"], [role="button"]'));
                el = candidates.find(c => (c.innerText || c.value || c.getAttribute('aria-label') || c.getAttribute('title') || '').toLowerCase().includes(query));
            }}
            if (el) {{
                el.style.outline = '3px solid #4F46E5';
                el.style.outlineOffset = '2px';
                el.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
                showAiRemoteToast('클릭 → ' + (el.innerText || el.value || el.tagName).trim().slice(0, 28));
                setTimeout(() => el.click(), 180);
                return 'Clicked: ' + (el.innerText || el.value || el.tagName).slice(0, 50);
            }}
            showAiRemoteToast('요소를 찾지 못함: ' + query);
            return 'Element not found: ' + query;
        }})();
        """

    if act_type in ("fill", "write"):
        submit_after = bool(action.get("submit", False))
        submit_js = """
            const form = el.closest('form');
            if (form) {
                setTimeout(() => form.submit(), 250);
            } else {
                el.dispatchEvent(new KeyboardEvent('keydown', {key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true}));
            }
        """ if submit_after else ""
        return f"""
        (() => {{
            {toast_helper}
            const query = {target_json}.toLowerCase().replace(/^#/, '');
            const textVal = {value_json};
            let el = document.querySelector(`[data-bside-id="${{query}}"]`);
            if (!el) {{
                const inputs = Array.from(document.querySelectorAll('textarea, input[type="text"], input[type="search"], input:not([type]), [contenteditable="true"]'))
                    .filter(i => i.getBoundingClientRect().width > 0);
                if (query && query !== 'search' && query !== 'auto') {{
                    el = inputs.find(i =>
                        (i.placeholder || '').toLowerCase().includes(query) ||
                        (i.name || '').toLowerCase().includes(query) ||
                        (i.getAttribute('aria-label') || '').toLowerCase().includes(query) ||
                        (i.id || '').toLowerCase().includes(query)
                    );
                }}
                if (!el) {{
                    el = document.activeElement && (document.activeElement.tagName === 'TEXTAREA' || document.activeElement.tagName === 'INPUT' || document.activeElement.isContentEditable)
                        ? document.activeElement
                        : inputs[0];
                }}
            }}
            if (el) {{
                el.focus();
                el.style.outline = '3px solid #10B981';
                el.style.outlineOffset = '2px';
                if (el.isContentEditable) {{
                    el.innerText = textVal;
                }} else {{
                    el.value = textVal;
                }}
                el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                showAiRemoteToast('자동 작성 완료 → "' + textVal.slice(0, 26) + '"');
                {submit_js}
                return 'Filled input with: ' + textVal;
            }}
            showAiRemoteToast('입력란을 찾지 못했습니다');
            return 'Input element not found';
        }})();
        """

    if act_type == "highlight":
        return """
        (() => {
            """ + toast_helper + """
            const els = document.querySelectorAll('[data-bside-id], h1, h2, a[href], button, input, textarea');
            let count = 0;
            els.forEach((el, idx) => {
                if (idx < 30 && el.getBoundingClientRect().width > 0) {
                    el.style.outline = '2px dashed #4F46E5';
                    el.style.outlineOffset = '2px';
                    count++;
                }
            });
            showAiRemoteToast('페이지 핵심 요소 ' + count + '개 스캔 및 표시');
            return 'Highlighted ' + count + ' interactive elements';
        })();
        """

    return "'No-op'"


def build_vault_login_autofill_js(
    username: str,
    password: str,
    auto_submit: bool = False,
    silent_if_no_form: bool = False,
) -> str:
    """
    Builds JS to automatically detect and fill login forms (username/email/ID + password)
    on modern web apps (React/Vue/Next.js/Vanilla DOM) using native HTMLInputElement value setters
    so framework state updates properly, and optionally clicks the login/submit button!
    """
    user_json = json.dumps(username or "", ensure_ascii=False)
    pw_json = json.dumps(password or "", ensure_ascii=False)
    submit_flag = "true" if auto_submit else "false"
    silent_flag = "true" if silent_if_no_form else "false"

    return f"""
    (() => {{
        const showVaultToast = (msg, bg = 'rgba(16,185,129,0.95)') => {{
            let badge = document.getElementById('bside-ai-remote-toast');
            if (!badge) {{
                badge = document.createElement('div');
                badge.id = 'bside-ai-remote-toast';
                badge.style.cssText = 'position:fixed;bottom:24px;right:24px;z-index:2147483647;color:#fff;padding:11px 18px;border-radius:14px;font-family:sans-serif;font-size:13px;font-weight:700;box-shadow:0 8px 24px rgba(0,0,0,0.25);border:1px solid rgba(255,255,255,0.2);transition:opacity 0.3s;';
                document.body.appendChild(badge);
            }}
            badge.style.background = bg;
            badge.innerText = '🔐 Bside Vault: ' + msg;
            badge.style.opacity = '1';
            setTimeout(() => {{ if (badge) badge.style.opacity = '0'; }}, 3200);
        }};

        const setNativeValue = (el, val) => {{
            if (!el) return;
            el.focus();
            const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value')?.set;
            if (setter) {{
                setter.call(el, val);
            }} else {{
                el.value = val;
            }}
            el.dispatchEvent(new Event('input', {{ bubbles: true }}));
            el.dispatchEvent(new Event('change', {{ bubbles: true }}));
            el.style.outline = '2.5px solid #10B981';
            el.style.outlineOffset = '2px';
        }};

        const isVisible = (el) => {{
            if (!el) return false;
            const r = el.getBoundingClientRect();
            return r.width > 10 && r.height > 10 && window.getComputedStyle(el).visibility !== 'hidden';
        }};

        const pwInputs = Array.from(document.querySelectorAll('input[type="password"]')).filter(isVisible);
        const pwEl = pwInputs[0] || null;

        const allTextInputs = Array.from(document.querySelectorAll(
            'input[type="text"], input[type="email"], input[type="tel"], input:not([type])'
        )).filter(isVisible);

        let userEl = allTextInputs.find(i => {{
            const meta = (
                (i.name || '') + ' ' +
                (i.id || '') + ' ' +
                (i.placeholder || '') + ' ' +
                (i.getAttribute('autocomplete') || '') + ' ' +
                (i.getAttribute('aria-label') || '')
            ).toLowerCase();
            return /user|login|email|id|account|아이디|이메일|계정|학번|사번/.test(meta);
        }});

        if (!userEl && pwEl) {{
            const form = pwEl.closest('form') || document.body;
            const formInputs = Array.from(form.querySelectorAll('input')).filter(isVisible);
            const pwIdx = formInputs.indexOf(pwEl);
            if (pwIdx > 0) {{
                userEl = formInputs[pwIdx - 1];
            }}
        }}

        if (!userEl && !pwEl) {{
            if (!{silent_flag}) {{
                showVaultToast('현재 페이지에서 로그인 입력란을 찾지 못했습니다.', 'rgba(239,68,68,0.92)');
            }}
            return {{ ok: false, reason: 'no_login_fields' }};
        }}

        const userVal = {user_json};
        const pwVal = {pw_json};

        if (userEl && userVal) setNativeValue(userEl, userVal);
        if (pwEl && pwVal) setNativeValue(pwEl, pwVal);

        if ({submit_flag}) {{
            showVaultToast('아이디/비밀번호 자동 입력 및 로그인 실행 중...');
            setTimeout(() => {{
                const scope = (pwEl && pwEl.closest('form')) || (userEl && userEl.closest('form')) || document;
                const btns = Array.from(scope.querySelectorAll('button, input[type="submit"], [role="button"]')).filter(isVisible);
                const loginBtn = btns.find(b => {{
                    const t = (b.innerText || b.value || b.getAttribute('aria-label') || '').toLowerCase();
                    return /로그인|sign in|log in|login|확인|계속|continue|submit/.test(t);
                }}) || scope.querySelector('button[type="submit"], input[type="submit"]');

                if (loginBtn) {{
                    loginBtn.click();
                }} else if (pwEl && pwEl.closest('form')) {{
                    pwEl.closest('form').submit();
                }} else if (pwEl) {{
                    pwEl.dispatchEvent(new KeyboardEvent('keydown', {{ key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true }}));
                }}
            }}, 280);
        }} else {{
            showVaultToast('저장된 계정(' + userVal + ') 자동 입력 완료!');
        }}

        return {{ ok: true, filledUser: Boolean(userEl), filledPw: Boolean(pwEl) }};
    }})();
    """


def build_vault_card_autofill_js(card: Dict[str, Any]) -> str:
    """
    Builds JS to automatically detect and fill payment/credit card fields
    (Card Number, Expiry MM/YY, CVC/CVV, Cardholder Name) on checkout pages.
    """
    num_raw = re.sub(r"[^0-9]", "", str(card.get("number", "")))
    expiry = str(card.get("expiry", ""))
    cvc = str(card.get("cvc", ""))
    holder = str(card.get("cardholder", ""))
    label = str(card.get("label", "저장된 카드"))

    num_json = json.dumps(num_raw, ensure_ascii=False)
    exp_json = json.dumps(expiry, ensure_ascii=False)
    cvc_json = json.dumps(cvc, ensure_ascii=False)
    holder_json = json.dumps(holder, ensure_ascii=False)
    label_json = json.dumps(label, ensure_ascii=False)

    return f"""
    (() => {{
        const showVaultToast = (msg, bg = 'rgba(79,70,229,0.95)') => {{
            let badge = document.getElementById('bside-ai-remote-toast');
            if (!badge) {{
                badge = document.createElement('div');
                badge.id = 'bside-ai-remote-toast';
                badge.style.cssText = 'position:fixed;bottom:24px;right:24px;z-index:2147483647;color:#fff;padding:11px 18px;border-radius:14px;font-family:sans-serif;font-size:13px;font-weight:700;box-shadow:0 8px 24px rgba(0,0,0,0.25);border:1px solid rgba(255,255,255,0.2);transition:opacity 0.3s;';
                document.body.appendChild(badge);
            }}
            badge.style.background = bg;
            badge.innerText = '💳 Bside Vault: ' + msg;
            badge.style.opacity = '1';
            setTimeout(() => {{ if (badge) badge.style.opacity = '0'; }}, 3400);
        }};

        const setNativeValue = (el, val) => {{
            if (!el || !val) return false;
            el.focus();
            const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value')?.set;
            if (setter) {{
                setter.call(el, val);
            }} else {{
                el.value = val;
            }}
            el.dispatchEvent(new Event('input', {{ bubbles: true }}));
            el.dispatchEvent(new Event('change', {{ bubbles: true }}));
            el.style.outline = '2.5px solid #4F46E5';
            el.style.outlineOffset = '2px';
            return true;
        }};

        const inputs = Array.from(document.querySelectorAll('input')).filter(el => {{
            const r = el.getBoundingClientRect();
            return r.width > 10 && r.height > 10;
        }});

        const metaOf = (el) => (
            (el.name || '') + ' ' +
            (el.id || '') + ' ' +
            (el.placeholder || '') + ' ' +
            (el.getAttribute('autocomplete') || '') + ' ' +
            (el.getAttribute('aria-label') || '')
        ).toLowerCase();

        let filledCount = 0;

        const numEl = inputs.find(i => /cc-number|cardnumber|card_number|card-number|카드번호|카드 번호|pan/.test(metaOf(i)));
        const expEl = inputs.find(i => /cc-exp|expiry|exp_date|exp-date|mm\\\/yy|유효기간|만료/.test(metaOf(i)));
        const cvcEl = inputs.find(i => /cc-csc|cvc|cvv|security code|보안코드|뒷면/.test(metaOf(i)));
        const nameEl = inputs.find(i => /cc-name|cardholder|card_holder|명의자|카드소유자|이름/.test(metaOf(i)));

        if (setNativeValue(numEl, {num_json})) filledCount++;
        if (setNativeValue(expEl, {exp_json})) filledCount++;
        if (setNativeValue(cvcEl, {cvc_json})) filledCount++;
        if (setNativeValue(nameEl, {holder_json})) filledCount++;

        // Fallback: if no explicit card field matched but an input is currently focused, fill card number there
        if (filledCount === 0 && document.activeElement && document.activeElement.tagName === 'INPUT') {{
            if (setNativeValue(document.activeElement, {num_json})) filledCount++;
        }}

        if (filledCount > 0) {{
            showVaultToast({label_json} + ' 결제 정보 (' + filledCount + '개 항목) 자동 입력 완료!');
            return {{ ok: true, count: filledCount }};
        }} else {{
            showVaultToast('결제 입력란을 찾지 못했습니다. 카드번호 입력칸을 클릭한 뒤 다시 시도해 주세요.', 'rgba(239,68,68,0.92)');
            return {{ ok: false, count: 0 }};
        }}
    }})();
    """


def generate_visual_svg_card(title: str, snapshot: Dict[str, Any], prompt: str) -> str:
    """Generates a sandboxed inline HTML/SVG visual chart card."""
    headings = snapshot.get("headings", [])
    interactives = snapshot.get("interactives", [])
    body_len = len(snapshot.get("bodyText", ""))

    h_count = len(headings)
    link_count = sum(1 for i in interactives if i.get("tag") == "a")
    btn_count = sum(1 for i in interactives if i.get("tag") in ("button", "input", "textarea"))
    text_score = min(100, max(15, body_len // 35))

    return f"""
    <div style="font-family:'Segoe UI',sans-serif; padding:12px; background:#FFFFFF; color:#1E1E20; border-radius:12px; border:1px solid #E5E3DC;">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
        <span style="font-size:12px; font-weight:700; color:#4F46E5;">📊 페이지 구조 & 요소 분석</span>
        <span style="font-size:10.5px; color:#666560;">{title[:26]}</span>
      </div>
      <svg viewBox="0 0 420 120" width="100%" height="120" style="background:#F9F8F4; border-radius:8px; padding:4px;">
        <text x="12" y="26" fill="#1E1E20" font-size="11" font-weight="600">헤딩 섹션 ({h_count})</text>
        <rect x="115" y="15" width="{min(260, max(24, h_count * 16))}" height="14" rx="5" fill="#4F46E5"/>
        <text x="12" y="54" fill="#1E1E20" font-size="11" font-weight="600">링크 요소 ({link_count})</text>
        <rect x="115" y="43" width="{min(260, max(24, link_count * 9))}" height="14" rx="5" fill="#8B5CF6"/>
        <text x="12" y="82" fill="#1E1E20" font-size="11" font-weight="600">입력/버튼 ({btn_count})</text>
        <rect x="115" y="71" width="{min(260, max(24, btn_count * 18))}" height="14" rx="5" fill="#10B981"/>
        <text x="12" y="110" fill="#1E1E20" font-size="11" font-weight="600">본문 밀도 ({text_score}%)</text>
        <rect x="115" y="99" width="{min(260, int(text_score * 2.5))}" height="14" rx="5" fill="#F59E0B"/>
      </svg>
    </div>
    """


class AgentWorker(QThread):
    """
    Fast, streaming-capable AgentWorker.
    - Supports real-time chunk streaming (`chunk_emitted`) so the user sees text immediately.
    - Supports AI Remote Page Control (`[ACTION:CLICK:...]`, `[ACTION:FILL:...]`, `[ACTION:SCROLL:...]`, `[ACTION:NAVIGATE:...]`).
    - Never switches to paid API automatically when a subscription model is selected;
      emits `quota_alert` popup if subscription quota/tokens are exhausted.
    """
    step_emitted = Signal(dict)        # {"tool": str, "status": str, "summary": str}
    chunk_emitted = Signal(str)        # progressive text update for fast UI feel
    action_requested = Signal(dict)    # {"action": "navigate"|"click"|"fill"|"scroll"|"highlight", ...}
    quota_alert = Signal(str, str)     # (title, message) -> triggers QMessageBox popup
    finished_reply = Signal(dict)      # {"content": str, "steps": list, "visual_html": str, "draft_card": dict}

    def __init__(
        self,
        prompt: str,
        page_snapshot: Dict[str, Any],
        open_tabs: List[Dict[str, str]],
        history: List[Dict[str, Any]],
        memories: List[Dict[str, Any]],
        settings: Dict[str, Any],
        conversation_messages: List[Dict[str, Any]],
    ):
        super().__init__()
        self.prompt = prompt
        self.snapshot = page_snapshot or {}
        self.open_tabs = open_tabs or []
        self.history = history or []
        self.memories = memories or []
        self.settings = settings or {}
        self.conversation_messages = conversation_messages or []

    def _needs_page_context(self) -> bool:
        """
        Determines whether the prompt actually asks about the current web page or DOM control.
        Skipping 2,000+ chars of DOM bodyText on simple greetings/questions makes CLI/LLM responses 3x-5x faster!
        """
        url = self.snapshot.get("url") or "bside://newtab"
        if url.startswith("bside://"):
            return False
        p = self.prompt.lower()
        page_keywords = [
            "페이지", "요약", "분석", "여기", "현재", "화면", "사이트", "탭", "링크", "버튼",
            "클릭", "입력", "작성", "채워", "스크롤", "원격", "조작", "제어", "스캔",
            "기사", "본문", "내용", "초안", "차트", "@", "page", "summary", "click", "fill", "scroll"
        ]
        return any(k in p for k in page_keywords) or len(self.prompt) > 40

    def run(self) -> None:
        steps: List[Dict[str, Any]] = []

        def emit_step(tool: str, summary: str, status: str = "done"):
            st = {"tool": tool, "status": status, "summary": summary}
            steps.append(st)
            self.step_emitted.emit(st)

        page_title = self.snapshot.get("title") or "현재 탭"
        page_url = self.snapshot.get("url") or "bside://newtab"
        prompt_lower = self.prompt.lower()

        # 1. Instant Remote Browser Control Actions (Executed immediately before/during LLM response!)
        nav_match = re.search(
            r"(https?://[^\s]+|네이버|구글|유튜브|깃허브|해커뉴스|위키백과|naver|google|youtube|github)",
            self.prompt,
            re.IGNORECASE,
        )
        if any(k in prompt_lower for k in ["열어", "이동", "가줘", "접속", "open ", "go to "]) and nav_match:
            raw_target = nav_match.group(1).lower()
            url_map = {
                "네이버": "https://www.naver.com",
                "naver": "https://www.naver.com",
                "구글": "https://www.google.com",
                "google": "https://www.google.com",
                "유튜브": "https://www.youtube.com",
                "youtube": "https://www.youtube.com",
                "깃허브": "https://github.com",
                "github": "https://github.com",
                "해커뉴스": "https://news.ycombinator.com",
                "위키백과": "https://ko.wikipedia.org",
            }
            target_url = url_map.get(raw_target, nav_match.group(1))
            emit_step("RemoteControl", f"페이지 원격 이동 → {target_url}")
            self.action_requested.emit({"action": "navigate", "url": target_url})

        if "스크롤" in prompt_lower or "scroll" in prompt_lower:
            direction = "up" if ("위" in prompt_lower or "up" in prompt_lower) else "down"
            emit_step("RemoteControl", f"페이지 원격 스크롤 ({direction.upper()})")
            self.action_requested.emit({"action": "scroll", "value": direction})

        if "클릭" in prompt_lower or "눌러" in prompt_lower or "click" in prompt_lower:
            m = re.search(r"['\"]([^'\"]+)['\"]|#(\d+)|([가-힣a-zA-Z0-9_]+)\s*(?:버튼|링크|메뉴|탭)?\s*(?:클릭|눌러)", self.prompt)
            target_lbl = (m.group(1) or m.group(2) or m.group(3)) if m else "검색"
            emit_step("RemoteControl", f"페이지 요소 원격 클릭: '{target_lbl}'")
            self.action_requested.emit({"action": "click", "target": target_lbl})

        if any(k in prompt_lower for k in ["입력", "채워", "작성해", "써줘", "검색해", "fill"]):
            m = re.search(r"['\"]([^'\"]+)['\"]", self.prompt)
            val_to_fill = m.group(1) if m else ""
            if not val_to_fill:
                # Extract phrase before 검색해/입력해
                m2 = re.search(r"([가-힣a-zA-Z0-9\s]{2,25}?)\s*(?:라고|으로)?\s*(?:입력|검색|작성|채워)", self.prompt)
                if m2:
                    val_to_fill = m2.group(1).strip()
            if val_to_fill:
                should_submit = "검색" in prompt_lower or "엔터" in prompt_lower
                emit_step("RemoteControl", f"페이지 입력란 원격 작성: '{val_to_fill}'")
                self.action_requested.emit(
                    {"action": "fill", "target": "auto", "value": val_to_fill, "submit": should_submit}
                )

        if any(k in prompt_lower for k in ["하이라이트", "강조", "요소 스캔", "@bsidewright"]):
            emit_step("RemoteControl", "페이지 조작 가능 요소 원격 하이라이트 표시")
            self.action_requested.emit({"action": "highlight", "target": "all"})

        if any(k in prompt_lower for k in ["로그인해", "로그인 해", "자동 로그인", "비밀번호 입력", "비번 입력", "계정 입력"]):
            emit_step("BsideVault", "Bside Vault 저장 계정으로 자동 입력 및 로그인 실행")
            self.action_requested.emit({"action": "vault_login", "submit": True})

        if any(k in prompt_lower for k in ["카드 입력", "카드번호 입력", "결제 입력", "결제카드 입력", "카드 자동"]):
            emit_step("BsideVault", "Bside Vault 저장 카드로 결제 정보 자동 입력")
            self.action_requested.emit({"action": "vault_card"})

        # 2. Optional @visualize chart or @draft-preview card
        visual_html = ""
        if any(k in prompt_lower for k in ["@visualize", "차트", "그래프", "시각화"]):
            visual_html = generate_visual_svg_card(page_title, self.snapshot, self.prompt)

        draft_card = None
        if any(k in prompt_lower for k in ["@draft-preview", "이메일 초안", "슬랙 초안", "공유 초안"]):
            excerpt = (self.snapshot.get("bodyText") or "")[:220].strip() or "현재 열려 있는 페이지의 핵심 요약입니다."
            draft_card = {
                "channel": "원격 작성 / 공유 초안",
                "recipient": "team@studio.at",
                "subject": f"[{page_title[:24]}] 핵심 내용 정리",
                "body": f"안녕하세요,\n\n'{page_title}' ({page_url}) 주요 내용을 공유합니다.\n\n• 핵심 요약: {excerpt}...\n\n감사합니다.",
            }

        # 3. Execute User-Selected Model (Subscription CLI OR API OR Built-in)
        model_choice = self.settings.get("default_model", "claude-sub")
        openai_key = (self.settings.get("openai_api_key") or os.environ.get("OPENAI_API_KEY") or "").strip()
        gemini_key = (self.settings.get("gemini_api_key") or os.environ.get("GEMINI_API_KEY") or "").strip()
        anthropic_key = (self.settings.get("anthropic_api_key") or os.environ.get("ANTHROPIC_API_KEY") or "").strip()

        reply_text: Optional[str] = None

        if model_choice in ("claude-sub", "codex-sub", "antigravity-sub") or model_choice.startswith(("claude:", "codex:", "antigravity:")):
            if ":" in model_choice:
                cli_key, sub_model_variant = model_choice.split(":", 1)
            else:
                cli_key = model_choice.replace("-sub", "")
                sub_model_variant = self.settings.get("selected_sub_model_name", "")

            effort_label = self.settings.get("reasoning_effort", "Extra High")
            fast_mode = bool(self.settings.get("fast_mode", True))
            display_name = f"{cli_key.capitalize()} 구독 ({sub_model_variant or '기본'} · {effort_label})"
            emit_step("AI Agent", f"{display_name} 실시간 응답 생성 중...")
            ok, cli_out = self._call_subscription_cli_streaming(cli_key, sub_model_variant, effort_label, fast_mode)
            if ok and cli_out:
                reply_text = self._parse_and_trigger_llm_actions(cli_out)
            else:
                self.quota_alert.emit(
                    f"{display_name} 사용량/연결 알림",
                    f"현재 선택하신 [{display_name}]에서 응답을 받을 수 없거나 구독 토큰을 모두 소모했습니다.\n\n"
                    f"• 상세 사유: {cli_out}\n\n"
                    f"👉 하단 모델 선택창에서 다른 구독 모델(Claude / Codex / Antigravity) 또는 API를 선택해 주세요.",
                )
                reply_text = (
                    f"⚠️ **[{display_name}] 토큰 소진 또는 연결 제한 알림**\n\n"
                    f"- **사유**: `{cli_out}`\n"
                    f"- 하단 드롭다운에서 다른 구독 모델 또는 API 모델을 직접 선택해 주세요."
                )

        elif model_choice == "claude-api":
            if not anthropic_key:
                self.quota_alert.emit("Anthropic API 키 필요", "우측 상단 ⚙ 설정에서 Anthropic API Key를 먼저 입력해 주세요.")
                reply_text = "⚠️ **Anthropic API Key가 설정되지 않았습니다.** 우측 상단 `⚙` 버튼에서 입력해 주세요."
            else:
                reply_text = self._call_anthropic("claude-3-5-sonnet-latest", anthropic_key)

        elif model_choice == "openai-api":
            if not openai_key:
                self.quota_alert.emit("OpenAI API 키 필요", "우측 상단 ⚙ 설정에서 OpenAI API Key를 먼저 입력해 주세요.")
                reply_text = "⚠️ **OpenAI API Key가 설정되지 않았습니다.** 우측 상단 `⚙` 버튼에서 입력해 주세요."
            else:
                reply_text = self._call_openai("gpt-4o-mini", openai_key)

        elif model_choice == "gemini-api":
            if not gemini_key:
                self.quota_alert.emit("Gemini API 키 필요", "우측 상단 ⚙ 설정에서 Gemini API Key를 먼저 입력해 주세요.")
                reply_text = "⚠️ **Gemini API Key가 설정되지 않았습니다.** 우측 상단 `⚙` 버튼에서 입력해 주세요."
            else:
                reply_text = self._call_gemini("gemini-2.5-flash", gemini_key)

        elif model_choice == "custom-local":
            base_url = self.settings.get("custom_base_url", "http://localhost:11434/v1")
            custom_model = self.settings.get("custom_model_name", "qwen2.5:7b")
            reply_text = self._call_openai(custom_model, "ollama", base_url=base_url)

        if not reply_text:
            reply_text = self._generate_builtin_response()
            self.chunk_emitted.emit(reply_text)

        self.finished_reply.emit(
            {
                "content": reply_text,
                "steps": steps,
                "visual_html": visual_html,
                "draft_card": draft_card,
            }
        )

    def _parse_and_trigger_llm_actions(self, text: str) -> str:
        """
        Parses remote-control action tags emitted by the AI (e.g. `[ACTION:CLICK:#3]`,
        `[ACTION:FILL:검색어]`, `[ACTION:SCROLL:down]`, `[ACTION:NAVIGATE:https://...]`)
        and executes them live on the active browser page!
        """
        pattern = re.compile(r"\[ACTION:(CLICK|FILL|SCROLL|NAVIGATE|HIGHLIGHT):([^\]]*)\]", re.IGNORECASE)
        for match in pattern.finditer(text):
            act = match.group(1).upper()
            arg = match.group(2).strip()
            if act == "CLICK":
                self.action_requested.emit({"action": "click", "target": arg})
            elif act == "FILL":
                if "|" in arg:
                    t, v = arg.split("|", 1)
                    self.action_requested.emit({"action": "fill", "target": t.strip(), "value": v.strip()})
                else:
                    self.action_requested.emit({"action": "fill", "target": "auto", "value": arg})
            elif act == "SCROLL":
                self.action_requested.emit({"action": "scroll", "value": arg or "down"})
            elif act == "NAVIGATE":
                self.action_requested.emit({"action": "navigate", "url": arg})
            elif act == "HIGHLIGHT":
                self.action_requested.emit({"action": "highlight", "target": "all"})

        cleaned = pattern.sub("", text).strip()
        return cleaned or text

    def _call_subscription_cli_streaming(
        self,
        provider: str,
        model_variant: str = "",
        effort_label: str = "Extra High",
        fast_mode: bool = True,
    ) -> Tuple[bool, str]:
        """
        Fast, low-latency CLI invocation with live stdout streaming (`chunk_emitted`)
        and full support for Model Variant + Reasoning Effort (Low / Medium / High / Extra High / Max / Ultrabrowse) + Fast mode!
        """
        status = get_subscription_auth_status()
        info = status.get(provider)
        if not info or not info.get("installed"):
            return False, f"{provider} CLI가 설치되어 있지 않습니다 (우측 상단 ⚙ 설정에서 연결 가능)"

        bin_path = info["bin"]
        ctx = self._build_system_context()
        if effort_label == "Ultrabrowse" and not ctx:
            # Ultrabrowse forces deep page & tab inspection
            ctx = (
                "당신은 Bside Ultrabrowse 심층 웹 분석 및 원격 제어 에이전트입니다.\n"
                f"[현재 페이지: {self.snapshot.get('title')} ({self.snapshot.get('url')})]\n"
                f"{(self.snapshot.get('bodyText') or '')[:1800]}"
            )
        full_input = f"{ctx}\n\n[사용자 질문/지시]\n{self.prompt}" if ctx else self.prompt
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000) if os.name == "nt" else 0

        # Map UI Effort (Low, Medium, High, Extra High, Max, Ultrabrowse) to CLI effort tokens
        eff_low = effort_label.lower()
        if fast_mode and eff_low not in ("max", "ultrabrowse"):
            cli_effort = "low"
        elif "low" in eff_low:
            cli_effort = "low"
        elif "medium" in eff_low:
            cli_effort = "medium"
        else:
            cli_effort = "high"

        if provider == "claude":
            # Map friendly Claude model names to valid claude CLI model aliases
            c_model = "sonnet"
            mv_low = (model_variant or "").lower()
            if "opus" in mv_low:
                c_model = "opus"
            elif "haiku" in mv_low:
                c_model = "haiku"
            cmd = [
                bin_path,
                "-p",
                full_input,
                "--model",
                c_model,
                "--output-format",
                "text",
                "--tools",
                "",
                "--no-session-persistence",
                "--strict-mcp-config",
                "--effort",
                cli_effort,
            ]
        elif provider == "codex":
            cmd = [
                bin_path,
                "exec",
                "--skip-git-repo-check",
                "-c",
                f'model_reasoning_effort="{cli_effort}"',
                full_input,
            ]
        elif provider == "antigravity":
            # Map friendly Antigravity / Gemini model names to agy.exe models
            a_model = "gemini-3.8-flash-low" if (fast_mode or "flash" in (model_variant or "").lower() or "luna" in (model_variant or "").lower()) else "gemini-2.5-pro"
            cmd = [
                bin_path,
                "-p",
                full_input,
                "--output-format",
                "text",
                "--model",
                a_model,
                "--effort",
                cli_effort,
                "--dangerously-skip-permissions",
                "--disable-slash-commands",
            ]
        else:
            cmd = [bin_path, "-p", full_input]

        try:
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                cwd=tempfile.gettempdir(),
                creationflags=creationflags,
                bufsize=1,
            )

            collected: List[str] = []
            if proc.stdout:
                for line in iter(proc.stdout.readline, ""):
                    if not line:
                        break
                    # Filter out codex/cli banner noise if any
                    if line.startswith("Reading additional input from stdin"):
                        continue
                    collected.append(line)
                    partial = "".join(collected).strip()
                    if partial:
                        self.chunk_emitted.emit(partial)

            proc.wait(timeout=45)
            stdout = "".join(collected).strip()
            stderr = (proc.stderr.read() if proc.stderr else "").strip()
            combined_low = (stdout + "\n" + stderr).lower()

            quota_keywords = [
                "rate limit",
                "quota",
                "insufficient_quota",
                "credit balance",
                "usage limit",
                "limit reached",
                "too many requests",
                "429",
            ]
            if any(k in combined_low for k in quota_keywords):
                return False, "구독 토큰/사용량 한도 소진 (Quota/Rate Limit Exceeded)"

            if proc.returncode == 0 and stdout:
                return True, stdout
            return False, (stderr[:140] or stdout[:140] or f"종료 코드 {proc.returncode}")
        except subprocess.TimeoutExpired:
            try:
                proc.kill()
            except Exception:
                pass
            return False, "구독 CLI 응답 시간 초과 (45초)"
        except Exception as e:
            return False, str(e)[:100]

    def _build_system_context(self) -> str:
        """
        Lightweight, fast system context.
        Only includes full page DOM snapshot when the user is on a web page AND asks about the page/remote control.
        """
        if not self._needs_page_context():
            return "당신은 Bside 브라우저의 AI 어시스턴트입니다. 한국어로 간결하고 친절하게 답변하세요."

        headings_str = ", ".join([h.get("text", "") for h in self.snapshot.get("headings", [])[:8]])
        interactives = self.snapshot.get("interactives", [])[:15]
        els_str = ", ".join([f"#{i.get('id')}:{i.get('label', '')[:20]}({i.get('tag')})" for i in interactives])
        body_excerpt = (self.snapshot.get("bodyText") or "")[:1100]

        return (
            "당신은 Bside 브라우저의 AI 페이지 분석 및 원격 제어 에이전트입니다. 한국어로 간결하게 답변하세요.\n"
            "사용자가 페이지 조작(클릭/입력/스크롤/이동)을 원하면 답변 끝에 다음 원격 제어 태그를 포함할 수 있습니다:\n"
            "[ACTION:CLICK:요소이름 또는 #번호] / [ACTION:FILL:입력할내용] / [ACTION:SCROLL:down 또는 up]\n\n"
            f"[현재 연결된 웹페이지]\n"
            f"- 제목: {self.snapshot.get('title')}\n"
            f"- 주소: {self.snapshot.get('url')}\n"
            f"- 주요 섹션: {headings_str}\n"
            f"- 조작 가능 요소: {els_str}\n"
            f"- 페이지 본문 요약용 발췌:\n{body_excerpt}"
        )

    def _call_openai(self, model: str, api_key: str, base_url: str = "https://api.openai.com/v1") -> Optional[str]:
        try:
            url = base_url.rstrip("/") + "/chat/completions"
            ctx = self._build_system_context()
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": ctx},
                    {"role": "user", "content": self.prompt},
                ],
                "temperature": 0.4,
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=25) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                out = data["choices"][0]["message"]["content"]
                self.chunk_emitted.emit(out)
                return self._parse_and_trigger_llm_actions(out)
        except Exception as e:
            self.quota_alert.emit("OpenAI API 호출 오류", f"OpenAI API 호출 중 오류가 발생했습니다:\n{e}")
            return f"⚠️ **OpenAI API 오류**: `{e}`"

    def _call_gemini(self, model: str, api_key: str) -> Optional[str]:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
            ctx = self._build_system_context()
            payload = {
                "contents": [
                    {
                        "role": "user",
                        "parts": [{"text": f"{ctx}\n\n질문: {self.prompt}"}],
                    }
                ]
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=25) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                out = data["candidates"][0]["content"]["parts"][0]["text"]
                self.chunk_emitted.emit(out)
                return self._parse_and_trigger_llm_actions(out)
        except Exception as e:
            self.quota_alert.emit("Gemini API 호출 오류", f"Gemini API 호출 중 오류가 발생했습니다:\n{e}")
            return f"⚠️ **Gemini API 오류**: `{e}`"

    def _call_anthropic(self, model: str, api_key: str) -> Optional[str]:
        try:
            url = "https://api.anthropic.com/v1/messages"
            ctx = self._build_system_context()
            payload = {
                "model": model,
                "max_tokens": 1200,
                "system": ctx,
                "messages": [{"role": "user", "content": self.prompt}],
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=25) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                out = data["content"][0]["text"]
                self.chunk_emitted.emit(out)
                return self._parse_and_trigger_llm_actions(out)
        except Exception as e:
            self.quota_alert.emit("Anthropic API 호출 오류", f"Anthropic API 호출 중 오류가 발생했습니다:\n{e}")
            return f"⚠️ **Anthropic API 오류**: `{e}`"

    def _generate_builtin_response(self) -> str:
        """Instant offline DOM analyzer & remote controller response."""
        title = self.snapshot.get("title") or "현재 탭"
        url = self.snapshot.get("url") or "bside://newtab"
        headings = self.snapshot.get("headings") or []
        interactives = self.snapshot.get("interactives") or []
        body_text = (self.snapshot.get("bodyText") or "").strip()
        p_low = self.prompt.lower()

        if "링크" in p_low or "버튼" in p_low or "요소" in p_low or "@bsidewright" in p_low:
            lines = [f"### 🕹️ `{title}` 원격 조작 가능 요소 (`{len(interactives)}개`)\n"]
            if interactives:
                lines.append("| 번호 | 종류 | 이름 / 텍스트 |")
                lines.append("|---|---|---|")
                for item in interactives[:10]:
                    lbl = item.get("label", "").replace("|", "/")[:34]
                    lines.append(f"| `#{item.get('id')}` | `{item.get('tag')}` | {lbl} |")
            else:
                lines.append("- 현재 화면에서 추출된 외부 버튼/입력 요소가 없습니다.")
            lines.append("\n💡 **원격 조작 팁**: 채팅창에 `'#1 클릭해줘'` 또는 `'검색창에 날씨 입력해줘'`라고 입력하면 AI가 즉시 페이지를 제어합니다.")
            return "\n".join(lines)

        lines = [f"### ✦ `{title}` 핵심 분석\n"]
        if headings:
            h_list = " · ".join([f"`{h.get('text')}`" for h in headings[:5]])
            lines.append(f"- **주요 섹션**: {h_list}")

        if body_text and not url.startswith("bside://"):
            sentences = [s.strip() for s in re.split(r"[.!?]\s+|\n+", body_text) if len(s.strip()) > 20]
            lines.append("\n**요약 내용:**")
            for s in sentences[:4]:
                lines.append(f"- {s[:150]}")
        else:
            lines.append("- 상단 주소창에서 원하시는 웹사이트로 이동한 뒤 질문하거나 원격 조작(클릭/입력/스크롤)을 지시해 보세요.")

        return "\n".join(lines)
