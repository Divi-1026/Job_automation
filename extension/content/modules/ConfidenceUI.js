// CareerSync ConfidenceUI.js
(() => {

  class ConfidenceUI {

    constructor() {
      this.prompt = null;
    }

    removeExistingPrompt() {
      if (this.prompt) {
        this.prompt.remove();
        this.prompt = null;
      }

      document
        .querySelectorAll(
          "[data-careersync-answer-prompt='true']"
        )
        .forEach(
          node =>
            node.remove()
        );
    }

    getType(field) {
      const el =
        field?.element;

      if (!el) {
        return "";
      }

      if (
        el.tagName
          ?.toLowerCase() ===
        "select"
      ) {
        return "select";
      }

      return String(
        field.type ||
        el.type ||
        el.tagName ||
        ""
      ).toLowerCase();
    }

    showPrompt({
      field,
      question,
      choices = [],
      index = 1,
      total = 1,
      onSave,
      onSkip
    }) {

      this.removeExistingPrompt();

      const type =
        this.getType(field);

      const overlay =
        document.createElement(
          "div"
        );

      overlay.setAttribute(
        "data-careersync-answer-prompt",
        "true"
      );

      Object.assign(
        overlay.style,
        {
          position: "fixed",
          inset: "0",
          zIndex:
            "2147483646",
          background:
            "rgba(15,23,42,0.22)",
          pointerEvents:
            "none"
        }
      );

      const card =
        document.createElement(
          "div"
        );

      Object.assign(
        card.style,
        {
          position: "fixed",
          right: "24px",
          top: "50%",
          transform:
            "translateY(-50%)",
          width: "390px",
          maxWidth:
            "calc(100vw - 32px)",
          maxHeight:
            "calc(100vh - 40px)",
          overflowY: "auto",
          zIndex:
            "2147483647",
          background: "#fff",
          border:
            "1px solid #dbe1ea",
          borderRadius:
            "16px",
          boxShadow:
            "0 24px 70px rgba(15,23,42,.28)",
          padding: "20px",
          fontFamily:
            "Arial, Helvetica, sans-serif",
          color: "#111827",
          pointerEvents:
            "auto"
        }
      );

      const head =
        document.createElement(
          "div"
        );

      Object.assign(
        head.style,
        {
          display: "flex",
          alignItems:
            "center",
          justifyContent:
            "space-between",
          gap: "12px",
          marginBottom:
            "12px"
        }
      );

      const title =
        document.createElement(
          "div"
        );

      title.textContent =
        "CareerSync needs your answer";

      Object.assign(
        title.style,
        {
          fontSize: "16px",
          fontWeight: "700"
        }
      );

      const progress =
        document.createElement(
          "div"
        );

      progress.textContent =
        `${index} / ${total}`;

      Object.assign(
        progress.style,
        {
          fontSize: "12px",
          fontWeight: "700",
          color: "#2563eb",
          background:
            "#eff6ff",
          padding: "5px 8px",
          borderRadius:
            "999px"
        }
      );

      head.append(
        title,
        progress
      );

      const questionText =
        document.createElement(
          "div"
        );

      questionText.textContent =
        question ||
        "Please answer this field.";

      Object.assign(
        questionText.style,
        {
          fontSize: "14px",
          fontWeight: "600",
          lineHeight: "1.5",
          marginBottom:
            "14px"
        }
      );

      const inputArea =
        document.createElement(
          "div"
        );

      inputArea.style.marginBottom =
        "10px";

      let control;

      // Dropdown / radio
      if (
        (
          type === "select" ||
          type === "radio" ||
          type === "custom-select"
        ) &&
        choices.length
      ) {

        control =
          document.createElement(
            "select"
          );

        const placeholder =
          document.createElement(
            "option"
          );

        placeholder.value =
          "";

        placeholder.textContent =
          "Select an answer";

        placeholder.disabled =
          true;

        placeholder.selected =
          true;

        control.appendChild(
          placeholder
        );

        choices.forEach(
          choice => {

            const option =
              document.createElement(
                "option"
              );

            option.value =
              choice.value ??
              choice.label;

            option.textContent =
              choice.label ??
              choice.value;

            control.appendChild(
              option
            );
          }
        );

      }

      // Checkbox
      else if (
        type === "checkbox"
      ) {

        control =
          document.createElement(
            "select"
          );

        const placeholder =
          document.createElement(
            "option"
          );

        placeholder.value =
          "";

        placeholder.textContent =
          "Select Yes or No";

        placeholder.disabled =
          true;

        placeholder.selected =
          true;

        control.appendChild(
          placeholder
        );

        ["Yes", "No"]
          .forEach(
            value => {

              const option =
                document.createElement(
                  "option"
                );

              option.value =
                value;

              option.textContent =
                value;

              control.appendChild(
                option
              );
            }
          );

      }

      // Textarea
      else if (
        field?.element
          ?.tagName
          ?.toLowerCase() ===
        "textarea"
      ) {

        control =
          document.createElement(
            "textarea"
          );

        control.placeholder =
          "Type your answer";

        control.style.minHeight =
          "110px";

        control.style.resize =
          "vertical";

      }

      // Normal input
      else {

        control =
          document.createElement(
            "input"
          );

        control.type =
          [
            "date",
            "number",
            "email",
            "url",
            "tel"
          ].includes(type)
            ? type
            : "text";

        if (
          type !== "date"
        ) {
          control.placeholder =
            "Type your answer";
        }
      }

      Object.assign(
        control.style,
        {
          width: "100%",
          padding:
            "11px 12px",
          border:
            "1px solid #cbd5e1",
          borderRadius:
            "9px",
          background:
            "#fff",
          color:
            "#111827",
          fontSize:
            "14px",
          outline:
            "none",
          boxSizing:
            "border-box"
        }
      );

      inputArea.appendChild(
        control
      );

      const helper =
        document.createElement(
          "div"
        );

      helper.textContent =
        "CareerSync will save this answer and reuse it next time.";

      Object.assign(
        helper.style,
        {
          fontSize: "12px",
          lineHeight: "1.45",
          color: "#64748b",
          marginBottom:
            "16px"
        }
      );

      const error =
        document.createElement(
          "div"
        );

      Object.assign(
        error.style,
        {
          display: "none",
          fontSize: "12px",
          color:
            "#dc2626",
          background:
            "#fef2f2",
          border:
            "1px solid #fecaca",
          padding:
            "8px 10px",
          borderRadius:
            "8px",
          marginBottom:
            "12px"
        }
      );

      const buttons =
        document.createElement(
          "div"
        );

      Object.assign(
        buttons.style,
        {
          display: "flex",
          gap: "10px",
          justifyContent:
            "flex-end"
        }
      );

      const skip =
        document.createElement(
          "button"
        );

      skip.type =
        "button";

      skip.textContent =
        "Skip";

      const save =
        document.createElement(
          "button"
        );

      save.type =
        "button";

      save.textContent =
        "Save & Fill";

      Object.assign(
        skip.style,
        {
          border:
            "1px solid #cbd5e1",
          background:
            "#fff",
          color:
            "#475569",
          borderRadius:
            "9px",
          padding:
            "9px 14px",
          cursor:
            "pointer",
          fontSize:
            "13px",
          fontWeight:
            "600"
        }
      );

      Object.assign(
        save.style,
        {
          border:
            "none",
          background:
            "#2563eb",
          color:
            "#fff",
          borderRadius:
            "9px",
          padding:
            "9px 14px",
          cursor:
            "pointer",
          fontSize:
            "13px",
          fontWeight:
            "700"
        }
      );

      buttons.append(
        skip,
        save
      );

      card.append(
        head,
        questionText,
        inputArea,
        helper,
        error,
        buttons
      );

      overlay.appendChild(
        card
      );

      document.documentElement
        .appendChild(
          overlay
        );

      this.prompt =
        overlay;

      const showError =
        message => {

          error.textContent =
            message;

          error.style.display =
            "block";
        };

      const close =
        () => {

          this.removeExistingPrompt();
        };

      const handleSave =
        async () => {

          error.style.display =
            "none";

          const answer =
            String(
              control.value ??
              ""
            ).trim();

          if (!answer) {

            showError(
              "Please enter or select an answer."
            );

            control.focus();
            return;
          }

          save.disabled =
            true;

          skip.disabled =
            true;

          save.textContent =
            "Saving...";

          try {

            await onSave(
              answer
            );

            close();

          } catch (e) {

            save.disabled =
              false;

            skip.disabled =
              false;

            save.textContent =
              "Save & Fill";

            showError(
              e?.message ||
              "Could not save this answer."
            );
          }
        };

      const handleSkip =
        () => {

          close();

          if (
            typeof onSkip ===
            "function"
          ) {
            onSkip();
          }
        };

      save.addEventListener(
        "click",
        handleSave
      );

      skip.addEventListener(
        "click",
        handleSkip
      );

      control.addEventListener(
        "keydown",
        event => {

          if (
            event.key ===
              "Enter" &&
            field?.element
              ?.tagName
              ?.toLowerCase() !==
              "textarea"
          ) {

            event.preventDefault();

            handleSave();
          }

          if (
            event.key ===
            "Escape"
          ) {

            event.preventDefault();

            handleSkip();
          }
        }
      );

      setTimeout(
        () =>
          control.focus(),
        50
      );
    }
  }

  window.CareerSyncConfidenceUI =
    ConfidenceUI;

})();