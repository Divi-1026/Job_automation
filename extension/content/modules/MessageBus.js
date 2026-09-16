// ============================================================
// CareerSync Autofill
// MessageBus.js
//
// Communication helper:
// content script <-> extension background
// ============================================================

class MessageBus {
  static send(type, payload = {}) {
    return new Promise((resolve, reject) => {
      try {
        chrome.runtime.sendMessage(
          {
            type,
            payload
          },
          (response) => {
            if (chrome.runtime.lastError) {
              reject(
                new Error(
                  chrome.runtime.lastError.message
                )
              );
              return;
            }

            resolve(response);
          }
        );
      } catch (error) {
        reject(error);
      }
    });
  }


  static on(type, callback) {
    chrome.runtime.onMessage.addListener(
      (message, sender, sendResponse) => {
        if (!message || message.type !== type) {
          return;
        }

        try {
          const result = callback(
            message.payload || {},
            sender
          );

          if (
            result &&
            typeof result.then === "function"
          ) {
            result
              .then(sendResponse)
              .catch((error) => {
                sendResponse({
                  success: false,
                  error: error.message
                });
              });

            return true;
          }

          sendResponse(result);

        } catch (error) {
          sendResponse({
            success: false,
            error: error.message
          });
        }
      }
    );
  }
}


window.CareerSyncMessageBus = MessageBus;