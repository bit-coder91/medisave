import { auth, configResult, onAuthStateChanged, signOut } from "./firebase.js";

const account = document.getElementById("account-label");
const login = document.getElementById("login-link");
const signup = document.getElementById("signup-link");
const logout = document.getElementById("logout-button");
const searchNote = document.getElementById("search-auth-note");

let resolveReady;
const ready = new Promise((resolve) => { resolveReady = resolve; });
const state = { enabled: configResult.enabled, user: null, ready };
window.MediSaveAuth = {
  state,
  config: configResult,
  ready,
  async token() {
    await ready;
    if (!state.enabled) return "";
    if (!state.user) {
      location.assign(`/login.html?next=${encodeURIComponent(location.pathname + location.search + location.hash)}`);
      throw new Error("Sign in to search.");
    }
    return state.user.getIdToken();
  },
};

function render() {
  if (!state.enabled) {
    account.textContent = "Demo mode";
    searchNote.textContent = "Demo search uses illustrative India listings. Configure Firebase to enable accounts and community requests.";
    login.hidden = false;
    signup.hidden = false;
    logout.hidden = true;
  } else if (state.user) {
    account.textContent = state.user.displayName || state.user.email || "Signed in";
    searchNote.textContent = "Signed in. Search by brand, active ingredient, or a likely spelling.";
    login.hidden = true;
    signup.hidden = true;
    logout.hidden = false;
  } else {
    account.textContent = "Sign in to search";
    searchNote.textContent = "Sign in to search the medicine catalog.";
    login.hidden = false;
    signup.hidden = false;
    logout.hidden = true;
  }
}

logout.addEventListener("click", () => signOut(auth));

if (state.enabled) {
  onAuthStateChanged(auth, (user) => {
    state.user = user;
    render();
    resolveReady();
  });
} else {
  render();
  resolveReady();
}
