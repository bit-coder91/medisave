import {
  auth,
  configResult,
  createUserWithEmailAndPassword,
  signInWithEmailAndPassword,
  updateProfile,
  sendPasswordResetEmail,
} from "./firebase.js";

const form = document.getElementById("auth-form");
const status = document.getElementById("auth-status");
const submit = document.getElementById("auth-submit");
const mode = document.body.dataset.mode;
const next = new URLSearchParams(location.search).get("next");
const destination = next && next.startsWith("/") && !next.startsWith("//") ? next : "/";

function say(message, error = false) {
  status.textContent = message;
  status.classList.toggle("error", error);
}

function friendlyError(error) {
  const messages = {
    "auth/email-already-in-use": "An account already uses this email. Try signing in.",
    "auth/invalid-email": "Enter a valid email address.",
    "auth/invalid-credential": "Email or password is incorrect.",
    "auth/weak-password": "Use at least 8 characters for your password.",
    "auth/too-many-requests": "Too many attempts. Please wait a little and try again.",
    "auth/network-request-failed": "Connection failed. Check your internet and try again.",
  };
  return messages[error.code] || "We could not complete that request. Please try again.";
}

if (!configResult.enabled) {
  say(`Firebase is not configured for this deployment yet. Add the required environment values in Vercel or .env.local: ${configResult.missing.join(", ")}.`, true);
  submit.disabled = true;
  form.querySelectorAll("input").forEach((input) => { input.disabled = true; });
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!auth) return;
  submit.disabled = true;
  say(mode === "signup" ? "Creating your account…" : "Signing you in…");
  const email = document.getElementById("email").value.trim();
  const password = document.getElementById("password").value;
  if (mode === "signup" && password !== document.getElementById("password-confirm").value) {
    say("Those passwords do not match. Please check them and try again.", true);
    submit.disabled = false;
    return;
  }
  try {
    if (mode === "signup") {
      const credential = await createUserWithEmailAndPassword(auth, email, password);
      const name = document.getElementById("name").value.trim();
      if (name) {
        try { await updateProfile(credential.user, { displayName: name }); } catch { /* Account creation still succeeded. */ }
      }
    } else {
      await signInWithEmailAndPassword(auth, email, password);
    }
    location.assign(destination);
  } catch (error) {
    say(friendlyError(error), true);
    submit.disabled = false;
  }
});

document.getElementById("reset-password")?.addEventListener("click", async () => {
  if (!auth) return;
  const email = document.getElementById("email").value.trim();
  if (!email) {
    say("Enter your email address first, then choose reset password.", true);
    return;
  }
  try {
    await sendPasswordResetEmail(auth, email);
    say("Password reset email sent. Check your inbox.");
  } catch (error) {
    say(friendlyError(error), true);
  }
});
