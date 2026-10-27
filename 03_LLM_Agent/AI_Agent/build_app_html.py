# build_app_html.py
import re
from pathlib import Path

def build():
    with open("resources/index.html", "r", encoding="utf-8") as f:
        src = f.read()

    # 1. Neutralino.js 스크립트 태그 제거
    src = re.sub(r'\s*<!-- Neutralino\.js Native Desktop Client -->\s*<script src="neutralino\.js"></script>\s*', '\n', src)

    # 2. 타이틀 변경
    src = src.replace("<title>Custom LLM Client</title>", "<title>Custom LLM Web Client</title>")

    # 3. JS 시작부터 McpClient 직전까지를 순수 LocalStorage 코드로 교체
    js_start_idx = src.find("<script>\n    // -----------------------------------------------------------\n    // [0] Neutralino Native Desktop 초기화")
    mcp_client_idx = src.find("// -----------------------------------------------------------\n    // [2] 통합 FastMCP 클라이언트 클래스")

    if js_start_idx == -1 or mcp_client_idx == -1:
        print(f"Index error: js_start={js_start_idx}, mcp_client={mcp_client_idx}")
        return

    new_pre_mcp = """<script>
    // -----------------------------------------------------------
    // [0] 브라우저 LocalStorage 기반 영구 스토리지 엔진
    // -----------------------------------------------------------
    const STORAGE_KEY_CONFIG = "custom_llm_app_config_v1";
    const STORAGE_KEY_ORDER = "custom_llm_sessions_order_v1";
    const STORAGE_PREFIX_SESSION = "custom_llm_session_v1_";

    function sanitizeFileName(name) {
      let clean = (name || "대화").replace(/[\\/:*?"<>|\\r\\n\\t]/g, "_").trim();
      if (!clean) clean = "대화";
      return clean;
    }

    const defaultConfig = {
      BASE_URL: "http://192.168.45.183:1234",
      API_KEY: "",
      MODEL_NAME: "google/gemma-4-e4b:2",
      TEMPERATURE: 0.2,
      THEME: "light",
      sidebarWidth: 200,
      DEFAULT_PROMPT: "",
      shortcuts: {
        "날씨": "오늘 서울의 날씨를 알려줘."
      },
      mcpServers: {
        skills_http: {
          name: "skills_http",
          type: "http",
          url: "http://127.0.0.1:8002/mcp",
          enabled: false
        },
        skills_sse: {
          name: "skills_sse",
          type: "sse",
          url: "http://127.0.0.1:8002/sse",
          enabled: false
        },
        fs_http: {
          name: "fs_http",
          type: "http",
          url: "http://127.0.0.1:8001/mcp",
          enabled: false
        },
        fs_sse: {
          name: "fs_sse",
          type: "sse",
          url: "http://127.0.0.1:8001/sse",
          enabled: false
        }
      }
    };

    let appConfig = Object.assign({}, defaultConfig);
    let sessionMap = new Map();
    let sessionOrder = [];
    let currentSessionId = null;
    let currentSessionData = null;
    let isProcessing = false;
    let currentAbortController = null;
    let mcpClients = {};
    let mcpToolsPool = [];

    async function loadConfig() {
      try {
        const stored = localStorage.getItem(STORAGE_KEY_CONFIG);
        if (stored) {
          const parsed = JSON.parse(stored);
          appConfig = Object.assign({}, defaultConfig, parsed);
          if (!appConfig.shortcuts || typeof appConfig.shortcuts !== "object") {
            appConfig.shortcuts = Object.assign({}, defaultConfig.shortcuts);
          }
          return appConfig;
        }
      } catch (e) {
        console.warn("Failed to load config from localStorage:", e);
      }
      appConfig = Object.assign({}, defaultConfig);
      if (!appConfig.shortcuts || typeof appConfig.shortcuts !== "object") {
        appConfig.shortcuts = Object.assign({}, defaultConfig.shortcuts);
      }
      saveConfigToStorage();
      return appConfig;
    }

    function saveConfigToStorage() {
      try {
        localStorage.setItem(STORAGE_KEY_CONFIG, JSON.stringify(appConfig));
      } catch (e) {
        console.error("Failed to save config to localStorage:", e);
      }
    }

    async function saveConfigToStorageAsync() {
      saveConfigToStorage();
    }

    """

    src = src[:js_start_idx] + new_pre_mcp + src[mcp_client_idx:]

    # 4. 세션 관리 섹션 [5] 교체
    sess_start_idx = src.find("// -----------------------------------------------------------\n    // [5] 대화 세션 관리")
    sess_end_idx = src.find("function renderConversationList() {")

    if sess_start_idx == -1 or sess_end_idx == -1:
        print(f"Session index error: sess_start={sess_start_idx}, sess_end={sess_end_idx}")
        return

    new_sess_code = """// -----------------------------------------------------------
    // [5] 대화 세션 관리 (LocalStorage 기반)
    // -----------------------------------------------------------
    function getUniqueRoomName(baseName, excludeName = null) {
      let clean = sanitizeFileName(baseName || "새 대화");
      let candidate = clean;
      let counter = 2;
      while (sessionMap.has(candidate) && candidate !== excludeName) {
        candidate = `${clean} ${counter++}`;
      }
      return candidate;
    }

    async function loadAllSessionsFromDisk() {
      sessionMap.clear();
      sessionOrder = [];

      try {
        const orderStored = localStorage.getItem(STORAGE_KEY_ORDER);
        if (orderStored) {
          sessionOrder = JSON.parse(orderStored) || [];
        }
      } catch (e) {
        sessionOrder = [];
      }

      const validOrder = [];
      for (const roomName of sessionOrder) {
        try {
          const key = STORAGE_PREFIX_SESSION + roomName;
          const dataStr = localStorage.getItem(key);
          if (dataStr) {
            const data = JSON.parse(dataStr);
            sessionMap.set(roomName, {
              systemPrompt: data.systemPrompt || "",
              messages: Array.isArray(data.messages) ? data.messages : []
            });
            validOrder.push(roomName);
          }
        } catch (readErr) {
          console.error("Failed to read session from localStorage:", roomName, readErr);
        }
      }

      // Check remaining keys in localStorage
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (key && key.startsWith(STORAGE_PREFIX_SESSION)) {
          const roomName = key.slice(STORAGE_PREFIX_SESSION.length);
          if (!sessionMap.has(roomName)) {
            try {
              const dataStr = localStorage.getItem(key);
              if (dataStr) {
                const data = JSON.parse(dataStr);
                sessionMap.set(roomName, {
                  systemPrompt: data.systemPrompt || "",
                  messages: Array.isArray(data.messages) ? data.messages : []
                });
                validOrder.push(roomName);
              }
            } catch (e) {}
          }
        }
      }

      sessionOrder = validOrder;
      saveSessionOrder();
    }

    function saveSessionOrder() {
      try {
        localStorage.setItem(STORAGE_KEY_ORDER, JSON.stringify(sessionOrder));
      } catch (e) {
        console.error("Failed to save session order:", e);
      }
    }

    function getConversationIndex() {
      return sessionOrder.map(roomName => ({
        id: roomName,
        title: roomName
      }));
    }

    function loadSessionData(roomName) {
      if (sessionMap.has(roomName)) {
        return sessionMap.get(roomName);
      }
      const newSession = {
        systemPrompt: appConfig.DEFAULT_PROMPT || "",
        messages: []
      };
      sessionMap.set(roomName, newSession);
      return newSession;
    }

    function saveCurrentSessionData() {
      if (!currentSessionId || !currentSessionData) return;
      if (currentSessionId === "__ONESHOT__") return;
      sessionMap.set(currentSessionId, currentSessionData);
      saveSessionDataAsync(currentSessionId);
    }

    async function saveSessionDataAsync(roomName) {
      if (roomName === "__ONESHOT__") return;
      const sess = sessionMap.get(roomName);
      if (!sess || sess.isOneShot) return;

      try {
        const payload = {
          systemPrompt: sess.systemPrompt || "",
          messages: sess.messages || []
        };
        localStorage.setItem(STORAGE_PREFIX_SESSION + roomName, JSON.stringify(payload));
      } catch (e) {
        console.error("Failed to write session to localStorage:", roomName, e);
      }
    }

    let oneShotSessionData = {
      systemPrompt: "",
      messages: [],
      isOneShot: true
    };

    function startOneShotSession() {
      if (isProcessing) return;
      currentSessionId = "__ONESHOT__";
      if (!oneShotSessionData.systemPrompt && appConfig.DEFAULT_PROMPT) {
        oneShotSessionData.systemPrompt = appConfig.DEFAULT_PROMPT;
      }
      currentSessionData = oneShotSessionData;
      renderConversationList();
      renderCurrentChatUI();
    }

    async function createNewSession() {
      if (isProcessing) return;
      const roomName = getUniqueRoomName("새 대화");
      const newSession = {
        systemPrompt: appConfig.DEFAULT_PROMPT || "",
        messages: []
      };

      sessionMap.set(roomName, newSession);
      sessionOrder.unshift(roomName);
      saveSessionOrder();

      await saveSessionDataAsync(roomName);
      switchSession(roomName);
    }

    function switchSession(roomName) {
      if (isProcessing) return;
      currentSessionId = roomName;
      currentSessionData = loadSessionData(roomName);
      renderConversationList();
      renderCurrentChatUI();
    }

    async function deleteSession(roomName, event) {
      if (event) event.stopPropagation();
      if (isProcessing) return;
      if (!confirm(`'${roomName}' 대화방을 삭제하시겠습니까?`)) return;

      sessionMap.delete(roomName);
      sessionOrder = sessionOrder.filter(x => x !== roomName);
      saveSessionOrder();

      try {
        localStorage.removeItem(STORAGE_PREFIX_SESSION + roomName);
      } catch (e) {}

      if (currentSessionId === roomName) {
        if (sessionOrder.length > 0) {
          switchSession(sessionOrder[0]);
        } else {
          await createNewSession();
        }
      } else {
        renderConversationList();
      }
    }

    async function editSessionTitle(oldRoomName, event) {
      if (event) event.stopPropagation();
      if (isProcessing) return;
      const targetSession = sessionMap.get(oldRoomName);
      if (!targetSession) return;

      const newTitle = prompt("대화방 이름을 입력하세요:", oldRoomName);
      if (newTitle && newTitle.trim() && newTitle.trim() !== oldRoomName) {
        const newRoomName = getUniqueRoomName(newTitle.trim(), oldRoomName);

        sessionMap.delete(oldRoomName);
        sessionMap.set(newRoomName, targetSession);

        const idx = sessionOrder.indexOf(oldRoomName);
        if (idx !== -1) {
          sessionOrder[idx] = newRoomName;
        }
        saveSessionOrder();

        try {
          localStorage.removeItem(STORAGE_PREFIX_SESSION + oldRoomName);
        } catch (e) {}

        await saveSessionDataAsync(newRoomName);

        if (currentSessionId === oldRoomName) {
          currentSessionId = newRoomName;
          currentSessionData = targetSession;
          document.getElementById("currentSessionTitle").textContent = newRoomName;
        }
        renderConversationList();
      }
    }

    """

    src = src[:sess_start_idx] + new_sess_code + src[sess_end_idx:]

    # 5. initApp 및 ready 이벤트 정리
    ready_idx = src.find("// Neutralino ready 이벤트 또는 DOMContentLoaded")
    if ready_idx != -1:
        src = src[:ready_idx] + "// 순수 브라우저 DOMContentLoaded 이벤트에서 초기화 실행\n    window.addEventListener(\"DOMContentLoaded\", initApp);\n  </script>\n</body>\n</html>"

    with open("resources/app.html", "w", encoding="utf-8") as f:
        f.write(src)

    print("app.html successfully built! Size:", len(src), "bytes")

if __name__ == "__main__":
    build()
