import { initializeApp } from "https://www.gstatic.com/firebasejs/12.19.0/firebase-app.js";
import {
  getAuth,
  createUserWithEmailAndPassword,
  signInWithEmailAndPassword,
  signOut,
  updateProfile,
  sendPasswordResetEmail,
  onAuthStateChanged,
} from "https://www.gstatic.com/firebasejs/12.19.0/firebase-auth.js";

let configResult;
try {
  const response = await fetch("/api/config", { cache: "no-store" });
  configResult = await response.json();
} catch {
  configResult = { enabled: false, missing: ["Firebase web configuration"] };
}

const auth = configResult.enabled ? getAuth(initializeApp(configResult.config)) : null;

export {
  auth,
  configResult,
  createUserWithEmailAndPassword,
  signInWithEmailAndPassword,
  signOut,
  updateProfile,
  sendPasswordResetEmail,
  onAuthStateChanged,
};
