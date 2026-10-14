const API_BASE = "http://127.0.0.1:5000";

const statusBox = document.getElementById("statusBox");
const connectionLoader = document.getElementById("connectionLoader");

const loginSection = document.getElementById("loginSection");
const connectedSection = document.getElementById("connectedSection");

const emailInput = document.getElementById("email");
const passwordInput = document.getElementById("password");

const loginBtn = document.getElementById("loginBtn");
const logoutBtn = document.getElementById("logoutBtn");
const profileBtn = document.getElementById("profileBtn");
const autofillBtn = document.getElementById("autofillBtn");
const profileBox = document.getElementById("profileBox");

const profileName = document.getElementById("profileName");
const profileEmail = document.getElementById("profileEmail");
const profilePhone = document.getElementById("profilePhone");
const profileCollege = document.getElementById("profileCollege");
const profileDegree = document.getElementById("profileDegree");
const profileSkills = document.getElementById("profileSkills");
const profileResume = document.getElementById("profileResume");

const messageBox = document.getElementById("message");


function showMessage(message = "", type = "") {
  messageBox.textContent = message;

  messageBox.classList.remove("error", "success");

  if (type) {
    messageBox.classList.add(type);
  }
}


function setConnectedUI(connected) {
  // Connection check is complete, so hide the startup spinner.
  connectionLoader.classList.add("hidden");
  statusBox.classList.remove("hidden");

  if (connected) {
    statusBox.textContent = "Connected to CareerSync";

    statusBox.classList.remove("disconnected");
    statusBox.classList.add("connected");

    loginSection.classList.add("hidden");
    connectedSection.classList.remove("hidden");
  } else {
    statusBox.textContent = "Not connected";

    statusBox.classList.remove("connected");
    statusBox.classList.add("disconnected");

    loginSection.classList.remove("hidden");
    connectedSection.classList.add("hidden");

    profileBox.classList.add("hidden");
  }
}


async function getToken() {
  const result = await chrome.storage.local.get([
    "careerSyncToken"
  ]);

  return result.careerSyncToken || null;
}


async function saveToken(token) {
  await chrome.storage.local.set({
    careerSyncToken: token
  });
}


async function removeToken() {
  await chrome.storage.local.remove([
    "careerSyncToken"
  ]);
}


async function verifyToken(token) {
  try {
    const response = await fetch(
      `${API_BASE}/extension/ping`,
      {
        method: "GET",
        headers: {
          Accept: "application/json",
          Authorization: `Bearer ${token}`
        }
      }
    );

    return response.ok;

  } catch (error) {

    console.error(
      "[CareerSync] Token verification error:",
      error
    );

    return false;
  }
}


/*
-----------------------------------------
LOGIN
-----------------------------------------
*/

loginBtn.addEventListener("click", async () => {

  showMessage("");

  const email = emailInput.value.trim();
  const password = passwordInput.value;

  if (!email) {
    showMessage(
      "Please enter your email.",
      "error"
    );

    return;
  }

  if (!password) {
    showMessage(
      "Please enter your password.",
      "error"
    );

    return;
  }

  loginBtn.disabled = true;
  loginBtn.textContent = "Connecting...";

  try {

    /*
      OAuth2PasswordRequestForm expects
      application/x-www-form-urlencoded
    */

    const formData = new URLSearchParams();

    formData.append("username", email);
    formData.append("password", password);

    const response = await fetch(
      `${API_BASE}/auth/login/form`,
      {
        method: "POST",

        headers: {
          "Content-Type":
            "application/x-www-form-urlencoded"
        },

        body: formData.toString()
      }
    );


    let data = {};

    try {
      data = await response.json();
    } catch (error) {
      console.error(
        "[CareerSync] Could not parse login response",
        error
      );
    }


    if (!response.ok) {

      const detail =
        data.detail ||
        "Invalid email or password.";

      throw new Error(detail);
    }


    /*
      Standard FastAPI OAuth response normally:
      {
        "access_token": "...",
        "token_type": "bearer"
      }

      token fallback is also supported.
    */

    const token =
      data.access_token ||
      data.token ||
      data.accessToken;


    if (!token) {
      console.error(
        "[CareerSync] Login response:",
        data
      );

      throw new Error(
        "Backend did not return an access token."
      );
    }


    const valid = await verifyToken(token);


    if (!valid) {
      throw new Error(
        "Login succeeded but token verification failed."
      );
    }


    await saveToken(token);


    /*
      Never store password.
    */

    passwordInput.value = "";


    setConnectedUI(true);


    showMessage(
      "CareerSync connected successfully.",
      "success"
    );


  } catch (error) {

    console.error(
      "[CareerSync] Login error:",
      error
    );


    setConnectedUI(false);


    showMessage(
      error.message ||
      "Could not connect to CareerSync.",
      "error"
    );

  } finally {

    loginBtn.disabled = false;
    loginBtn.textContent = "Connect";
  }
});
/*
-----------------------------------------
AUTOFILL CURRENT PAGE
-----------------------------------------
*/

autofillBtn.addEventListener("click", async () => {

  showMessage("");

  autofillBtn.disabled = true;
  autofillBtn.textContent = "Autofilling...";

  try {

    const [tab] = await chrome.tabs.query({
      active: true,
      currentWindow: true
    });


    if (!tab || !tab.id) {
      throw new Error(
        "Could not find the current tab."
      );
    }


    const response =
      await chrome.tabs.sendMessage(
        tab.id,
        {
          type: "CAREERSYNC_AUTOFILL"
        }
      );


    if (!response) {
      throw new Error(
        "No response from this page."
      );
    }


    if (!response.success) {
      throw new Error(
        response.error ||
        "Autofill failed."
      );
    }


    showMessage(
      `Detected ${response.detected} fields, filled ${response.filled}.`,
      "success"
    );


  } catch (error) {

    console.error(
      "[CareerSync] Autofill error:",
      error
    );


    showMessage(
      error.message ||
      "Could not autofill this page.",
      "error"
    );

  } finally {

    autofillBtn.disabled = false;
    autofillBtn.textContent =
      "Autofill This Form";
  }
});

/*
-----------------------------------------
LOAD PROFILE
-----------------------------------------
*/

profileBtn.addEventListener("click", async () => {

  showMessage("");

  profileBtn.disabled = true;
  profileBtn.textContent = "Loading...";

  try {

    const token = await getToken();


    if (!token) {
      throw new Error(
        "CareerSync is not connected."
      );
    }


    const response = await fetch(
      `${API_BASE}/extension/profile`,
      {
        method: "GET",

        headers: {
          Accept: "application/json",
          Authorization: `Bearer ${token}`
        }
      }
    );


    if (response.status === 401) {

      await removeToken();

      setConnectedUI(false);

      throw new Error(
        "Session expired. Please login again."
      );
    }


    if (!response.ok) {
      throw new Error(
        "Could not load CareerSync profile."
      );
    }


    const data = await response.json();


    console.log(
      "[CareerSync] Profile loaded:",
      data
    );


    const personal =
      data.personalInfo || {};


    const education =
      data.education || {};


    const professional =
      data.professional || {};


    const resume =
      data.resume || {};


    /*
      NAME
    */

    let fullName =
      personal.fullName || "";


    if (!fullName) {

      fullName = [
        personal.firstName,
        personal.lastName
      ]
        .filter(Boolean)
        .join(" ");
    }


    profileName.textContent =
      fullName || "-";


    /*
      EMAIL
    */

    profileEmail.textContent =
      personal.email || "-";


    /*
      PHONE
    */

    profilePhone.textContent =
      personal.phone || "-";


    /*
      COLLEGE
    */

    profileCollege.textContent =
      education.college || "-";


    /*
      DEGREE
    */

    const degreeParts = [
      education.degree,
      education.branch
    ].filter(Boolean);


    profileDegree.textContent =
      degreeParts.length
        ? degreeParts.join(" - ")
        : "-";


    /*
      SKILLS
    */

    const skills =
      professional.skills || [];


    if (Array.isArray(skills)) {

      profileSkills.textContent =
        skills.length
          ? skills.join(", ")
          : "-";

    } else {

      profileSkills.textContent =
        skills || "-";
    }


    /*
      RESUME
    */

    profileResume.textContent =
      resume.available
        ? (
            resume.filename ||
            "Resume available"
          )
        : "Not uploaded";


    profileBox.classList.remove("hidden");


    showMessage(
      "Profile loaded successfully.",
      "success"
    );


  } catch (error) {

    console.error(
      "[CareerSync] Profile error:",
      error
    );


    showMessage(
      error.message ||
      "Could not load profile.",
      "error"
    );

  } finally {

    profileBtn.disabled = false;
    profileBtn.textContent =
      "Load CareerSync Profile";
  }
});


/*
-----------------------------------------
LOGOUT / DISCONNECT
-----------------------------------------
*/

logoutBtn.addEventListener("click", async () => {

  await removeToken();

  passwordInput.value = "";

  setConnectedUI(false);

  showMessage(
    "CareerSync disconnected.",
    "success"
  );
});


/*
-----------------------------------------
INITIALIZE POPUP
-----------------------------------------
*/

async function initializePopup() {

  showMessage("");

  // While Chrome storage + backend token verification are running,
  // show only the connection spinner.
  connectionLoader.classList.remove("hidden");
  statusBox.classList.add("hidden");
  loginSection.classList.add("hidden");
  connectedSection.classList.add("hidden");
  profileBox.classList.add("hidden");

  try {

    const token = await getToken();

    if (!token) {
      setConnectedUI(false);
      return;
    }

    const valid =
      await verifyToken(token);

    if (valid) {

      setConnectedUI(true);

    } else {

      await removeToken();

      setConnectedUI(false);

      showMessage(
        "Session expired. Please login again.",
        "error"
      );
    }

  } catch (error) {

    console.error(
      "[CareerSync] Initial connection error:",
      error
    );

    setConnectedUI(false);

    showMessage(
      "Could not connect to CareerSync.",
      "error"
    );

  } finally {

    connectionLoader.classList.add("hidden");
  }
}


initializePopup();