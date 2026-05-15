import { register, go, state } from "../state.js";
import { startTutorial } from "../tutorial.js";

register("postlogin", { onEnter() {} });

export function bootPostLogin() {
  document.getElementById("startTutorialBtn").addEventListener("click", () => {
    state.tutorialActive = true;
    go("dashboard");
    setTimeout(startTutorial, 400);
  });
  document.getElementById("skipTutorialBtn").addEventListener("click", () => {
    state.tutorialActive = false;
    go("dashboard");
  });
}
