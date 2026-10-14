const API_BASE = "http://127.0.0.1:5000";


// ============================================================
// TOKEN
// ============================================================

async function getCareerSyncToken() {
  const result = await chrome.storage.local.get([
    "careerSyncToken"
  ]);

  return result.careerSyncToken || null;
}


// ============================================================
// AUTHENTICATED REQUEST
// ============================================================

async function authenticatedFetch(
  endpoint,
  options = {}
) {
  const token = await getCareerSyncToken();

  if (!token) {
    throw new Error(
      "CareerSync is not connected. Please login from the extension."
    );
  }

  const headers = {
    Accept: "application/json",
    ...(options.headers || {}),
    Authorization: `Bearer ${token}`
  };

  const response = await fetch(
    `${API_BASE}${endpoint}`,
    {
      ...options,
      headers
    }
  );

  if (response.status === 401) {
    await chrome.storage.local.remove([
      "careerSyncToken"
    ]);

    throw new Error(
      "CareerSync session expired. Please login again."
    );
  }

  let data = null;

  try {
    data = await response.json();
  } catch (error) {
    console.error(
      "[CareerSync] Could not parse response:",
      error
    );
  }

  if (!response.ok) {
    throw new Error(
      data?.detail ||
      data?.message ||
      `CareerSync request failed (${response.status}).`
    );
  }

  return data;
}


// ============================================================
// PROFILE - GET
// ============================================================

async function fetchCareerSyncProfile() {
  return await authenticatedFetch(
    "/extension/profile"
  );
}


// ============================================================
// PROFILE - UPDATE
// ============================================================

async function updateCareerSyncProfile(payload) {
  if (!payload || !payload.key) {
    throw new Error(
      "Extension profile update requires a key."
    );
  }

  return await authenticatedFetch(
    "/extension/profile",
    {
      method: "PATCH",

      headers: {
        "Content-Type": "application/json"
      },

      body: JSON.stringify({
        key: payload.key,
        value: payload.value
      })
    }
  );
}


// ============================================================
// MEMORY - GET
// ============================================================

async function fetchCareerSyncMemory() {
  const data = await authenticatedFetch(
    "/extension/memory"
  );

  return data.items || [];
}


// ============================================================
// MEMORY - SAVE
// ============================================================

async function saveCareerSyncMemory(payload) {
  return await authenticatedFetch(
    "/extension/memory",
    {
      method: "POST",

      headers: {
        "Content-Type": "application/json"
      },

      body: JSON.stringify(payload)
    }
  );
}


// ============================================================
// AI - BATCH SUGGESTIONS
// ============================================================

async function fetchCareerSyncAISuggestions(payload) {
  // Debug only field payload/response. Authentication tokens/API keys are
  // intentionally never printed.
  console.log("[CareerSync][BG AI REQUEST] /extension/ai/suggest-batch", payload);
  try {
    const data = await authenticatedFetch(
      "/extension/ai/suggest-batch",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload || { fields: [] })
      }
    );
    console.log("[CareerSync][BG AI RESPONSE]", data);
    return data;
  } catch (error) {
    console.error("[CareerSync][BG AI ERROR]", error);
    throw error;
  }
}


// ============================================================
// MESSAGE ROUTER
// ============================================================

chrome.runtime.onMessage.addListener(
  (message, sender, sendResponse) => {

    if (!message || !message.type) {
      return false;
    }


    // --------------------------------------------------------
    // GET PROFILE
    // --------------------------------------------------------

    if (message.type === "CAREERSYNC_GET_PROFILE") {

      fetchCareerSyncProfile()
        .then((profile) => {
          sendResponse({
            success: true,
            profile
          });
        })
        .catch((error) => {
          console.error(
            "[CareerSync] Profile error:",
            error
          );

          sendResponse({
            success: false,
            error: error.message
          });
        });

      return true;
    }


    // --------------------------------------------------------
    // UPDATE EXTENSION PROFILE
    // --------------------------------------------------------

    if (
      message.type ===
      "CAREERSYNC_UPDATE_EXTENSION_PROFILE"
    ) {
      const payload = message.payload || {};

      updateCareerSyncProfile(payload)
        .then((data) => {
          sendResponse({
            success: true,
            data
          });
        })
        .catch((error) => {
          console.error(
            "[CareerSync] Profile update error:",
            error
          );

          sendResponse({
            success: false,
            error: error.message
          });
        });

      return true;
    }


    // --------------------------------------------------------
    // GET MEMORY
    // --------------------------------------------------------

    if (message.type === "CAREERSYNC_GET_MEMORY") {

      fetchCareerSyncMemory()
        .then((items) => {
          sendResponse({
            success: true,
            items
          });
        })
        .catch((error) => {
          console.error(
            "[CareerSync] Memory fetch error:",
            error
          );

          sendResponse({
            success: false,
            error: error.message
          });
        });

      return true;
    }


    // --------------------------------------------------------
    // AI BATCH SUGGESTIONS
    // --------------------------------------------------------

    if (message.type === "CAREERSYNC_AI_SUGGEST_BATCH") {

      const payload = message.payload || { fields: [] };

      fetchCareerSyncAISuggestions(payload)
        .then((data) => {
          sendResponse({
            success: true,
            data
          });
        })
        .catch((error) => {
          console.error(
            "[CareerSync] AI suggestion error:",
            error
          );

          sendResponse({
            success: false,
            error: error.message
          });
        });

      return true;
    }


    // --------------------------------------------------------
    // SAVE MEMORY
    // --------------------------------------------------------

    if (message.type === "CAREERSYNC_SAVE_MEMORY") {

      const payload = message.payload || {};

      saveCareerSyncMemory(payload)
        .then((data) => {
          sendResponse({
            success: true,
            data
          });
        })
        .catch((error) => {
          console.error(
            "[CareerSync] Memory save error:",
            error
          );

          sendResponse({
            success: false,
            error: error.message
          });
        });

      return true;
    }


    return false;
  }
);


// ============================================================
// INSTALL
// ============================================================

chrome.runtime.onInstalled.addListener(() => {
  chrome.storage.local.set({
    careerSyncInstalled: true
  });

  console.log(
    "[CareerSync] Extension installed."
  );
});
