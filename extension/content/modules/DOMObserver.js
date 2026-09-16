// ============================================================
// CareerSync Autofill
// DOMObserver.js
//
// Watches dynamic pages for newly-added form fields.
// ============================================================

class DOMObserver {
  constructor(callback, delay = 500) {
    this.callback = callback;
    this.delay = delay;

    this.observer = null;
    this.timer = null;
  }


  start() {
    if (this.observer) {
      return;
    }

    this.observer = new MutationObserver(
      (mutations) => {
        let formChanged = false;

        for (const mutation of mutations) {
          if (mutation.type !== "childList") {
            continue;
          }

          for (const node of mutation.addedNodes) {
            if (!(node instanceof Element)) {
              continue;
            }

            if (
              node.matches?.(
                "input, textarea, select, form"
              ) ||
              node.querySelector?.(
                "input, textarea, select"
              )
            ) {
              formChanged = true;
              break;
            }
          }

          if (formChanged) {
            break;
          }
        }

        if (formChanged) {
          this.scheduleCallback();
        }
      }
    );


    this.observer.observe(
      document.documentElement,
      {
        childList: true,
        subtree: true
      }
    );


    console.log(
      "[CareerSync] DOM observer started."
    );
  }


  scheduleCallback() {
    clearTimeout(this.timer);

    this.timer = setTimeout(() => {
      try {
        this.callback();
      } catch (error) {
        console.error(
          "[CareerSync] DOM observer callback failed:",
          error
        );
      }
    }, this.delay);
  }


  stop() {
    if (this.observer) {
      this.observer.disconnect();
      this.observer = null;
    }

    clearTimeout(this.timer);

    console.log(
      "[CareerSync] DOM observer stopped."
    );
  }
}


window.CareerSyncDOMObserver = DOMObserver;