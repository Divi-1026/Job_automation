// ============================================================
// CareerSync Autofill
// FieldFiller.js
//
// Responsibility:
// - Fill native HTML fields
// - Trigger React/Angular/Vue events
// - Support text, date, select, checkbox and radio
// - Never make legal consent/privacy/declaration decisions
// ============================================================

class FieldFiller {
  fill(element, value) {
    if (!element) return false;

    if (
      value === undefined ||
      value === null ||
      value === ""
    ) {
      return false;
    }

    if (
      this.isUserDecisionOnlyElement(
        element
      )
    ) {
      console.log(
        "[CareerSync][FieldFiller] User-only decision left untouched."
      );

      return false;
    }

    try {
      const tag =
        element.tagName.toLowerCase();

      const type =
        (element.type || "")
          .toLowerCase();

      if (tag === "select") {
        return this.fillSelect(
          element,
          value
        );
      }

      if (type === "checkbox") {
        return this.fillCheckbox(
          element,
          value
        );
      }

      if (type === "radio") {
        return this.fillRadio(
          element,
          value
        );
      }

      if (
        tag === "input" ||
        tag === "textarea"
      ) {
        return this.fillTextField(
          element,
          this.prepareValue(
            element,
            value
          )
        );
      }

      return false;
    }
    catch (error) {
      console.error(
        "[CareerSync] Failed to fill field:",
        error
      );

      return false;
    }
  }

  fillTextField(
    element,
    value
  ) {
    const stringValue =
      String(value);

    this.setNativeValue(
      element,
      stringValue
    );

    this.dispatchEvents(element);
    this.markFilled(element);

    return (
      String(
        element.value ?? ""
      ) === stringValue
    );
  }

  setNativeValue(
    element,
    value
  ) {
    const prototype =
      element.tagName === "TEXTAREA"
        ? HTMLTextAreaElement.prototype
        : HTMLInputElement.prototype;

    const descriptor =
      Object.getOwnPropertyDescriptor(
        prototype,
        "value"
      );

    if (
      descriptor &&
      descriptor.set
    ) {
      descriptor.set.call(
        element,
        value
      );
    }
    else {
      element.value = value;
    }
  }

  fillSelect(
    element,
    value
  ) {
    const desired =
      this.normalize(value);

    const options =
      Array.from(
        element.options
      ).filter(
        option =>
          !option.disabled
      );

    let match =
      options.find(
        option =>
          this.normalize(
            option.value
          ) === desired
      );

    if (!match) {
      match =
        options.find(
          option =>
            this.normalize(
              option.textContent
            ) === desired
        );
    }

    if (!match) {
      match =
        options.find(option => {
          const optionText =
            this.normalize(
              option.textContent
            );

          if (
            !optionText ||
            !desired
          ) {
            return false;
          }

          return (
            optionText.includes(
              desired
            ) ||
            desired.includes(
              optionText
            )
          );
        });
    }

    if (!match) {
      return false;
    }

    const descriptor =
      Object.getOwnPropertyDescriptor(
        HTMLSelectElement.prototype,
        "value"
      );

    if (
      descriptor &&
      descriptor.set
    ) {
      descriptor.set.call(
        element,
        match.value
      );
    }
    else {
      element.value =
        match.value;
    }

    this.dispatchEvents(element);
    this.markFilled(element);

    return (
      element.value ===
      match.value
    );
  }

  fillCheckbox(
    element,
    value
  ) {
    if (
      this.isUserDecisionOnlyElement(
        element
      )
    ) {
      return false;
    }

    const shouldCheck =
      this.toBoolean(value);

    if (
      element.checked !==
      shouldCheck
    ) {
      element.click();
    }

    this.dispatchEvents(element);
    this.markFilled(element);

    return (
      element.checked ===
      shouldCheck
    );
  }

  fillRadio(
    element,
    value
  ) {
    if (
      this.isUserDecisionOnlyElement(
        element
      )
    ) {
      return false;
    }

    const desired =
      this.normalize(value);

    const ownValue =
      this.normalize(
        element.value
      );

    const label =
      this.getRadioLabel(
        element
      );

    const normalizedLabel =
      this.normalize(label);

    const matches =
      ownValue === desired ||
      normalizedLabel === desired ||
      (
        normalizedLabel &&
        desired &&
        (
          normalizedLabel.includes(
            desired
          ) ||
          desired.includes(
            normalizedLabel
          )
        )
      );

    if (!matches) {
      return false;
    }

    if (!element.checked) {
      element.click();
    }

    this.dispatchEvents(element);
    this.markFilled(element);

    return Boolean(
      element.checked
    );
  }

  prepareValue(
    element,
    value
  ) {
    const raw =
      String(value ?? "").trim();

    const type =
      String(
        element.type || ""
      ).toLowerCase();

    if (
      ![
        "date",
        "month",
        "datetime-local"
      ].includes(type)
    ) {
      return raw;
    }

    const parts =
      this.parseDate(raw);

    if (!parts) {
      return raw;
    }

    const yyyy =
      String(parts.year);

    const mm =
      String(parts.month)
        .padStart(2, "0");

    const dd =
      String(parts.day)
        .padStart(2, "0");

    if (type === "date") {
      return `${yyyy}-${mm}-${dd}`;
    }

    if (type === "month") {
      return `${yyyy}-${mm}`;
    }

    return `${yyyy}-${mm}-${dd}T00:00`;
  }

  parseDate(value) {
    let match =
      value.match(
        /^(\d{4})[-\/](\d{1,2})[-\/](\d{1,2})/
      );

    if (match) {
      return {
        year: Number(match[1]),
        month: Number(match[2]),
        day: Number(match[3])
      };
    }

    match =
      value.match(
        /^(\d{1,2})[-\/](\d{1,2})[-\/](\d{4})$/
      );

    if (match) {
      return {
        day: Number(match[1]),
        month: Number(match[2]),
        year: Number(match[3])
      };
    }

    return null;
  }

  isUserDecisionOnlyElement(
    element
  ) {
    const pieces = [
      element.getAttribute(
        "aria-label"
      ),
      element.getAttribute(
        "name"
      ),
      element.id,
      element.getAttribute(
        "placeholder"
      )
    ];

    if (element.id) {
      try {
        const label =
          document.querySelector(
            `label[for="${CSS.escape(element.id)}"]`
          );

        if (label) {
          pieces.push(
            label.innerText ||
            label.textContent ||
            ""
          );
        }
      }
      catch (_) {}
    }

    const container =
      element.closest(
        "label, fieldset, .form-group, .field, .form-field, .question, [role='group']"
      );

    if (container) {
      pieces.push(
        container.innerText ||
        container.textContent ||
        ""
      );
    }

    const text =
      this.normalize(
        pieces
          .filter(Boolean)
          .join(" ")
      );

    const patterns = [
      /\bi agree\b/,
      /\bi consent\b/,
      /\bconsent\b/,
      /\bprivacy policy\b/,
      /\bprivacy notice\b/,
      /\bterms and conditions\b/,
      /\bterms conditions\b/,
      /\bterms of use\b/,
      /\bterms of service\b/,
      /\bi acknowledge\b/,
      /\backnowledge\b/,
      /\bi understand\b/,
      /\bi have reviewed\b/,
      /\breviewed and understood\b/,
      /\bi authorize\b/,
      /\bauthorize\b/,
      /\bauthorization\b/,
      /\bauthorisation\b/,
      /\bi declare\b/,
      /\bdeclaration\b/,
      /\bi certify\b/,
      /\bcertify that\b/,
      /\bpersonal data\b/,
      /\bdata processing\b/,
      /\belectronic signature\b/,
      /\bbackground check consent\b/
    ];

    return patterns.some(
      pattern => pattern.test(text)
    );
  }

  getRadioLabel(element) {
    if (element.id) {
      try {
        const label =
          document.querySelector(
            `label[for="${CSS.escape(element.id)}"]`
          );

        if (label) {
          return (
            label.innerText ||
            label.textContent ||
            ""
          );
        }
      }
      catch (_) {}
    }

    const wrapped =
      element.closest("label");

    return wrapped
      ? wrapped.innerText ||
          wrapped.textContent ||
          ""
      : "";
  }

  dispatchEvents(element) {
    [
      "input",
      "change",
      "blur"
    ].forEach(eventName => {
      element.dispatchEvent(
        new Event(
          eventName,
          {
            bubbles: true
          }
        )
      );
    });
  }

  markFilled(element) {
    element.setAttribute(
      "data-careersync-filled",
      "true"
    );
  }

  toBoolean(value) {
    if (
      typeof value === "boolean"
    ) {
      return value;
    }

    return [
      "true",
      "yes",
      "y",
      "1",
      "checked"
    ].includes(
      this.normalize(value)
    );
  }

  normalize(value) {
    if (
      value === undefined ||
      value === null
    ) {
      return "";
    }

    return String(value)
      .toLowerCase()
      .replace(/[_-]+/g, " ")
      .replace(/[^\w\s]/g, " ")
      .replace(/\s+/g, " ")
      .trim();
  }
}

window.CareerSyncFieldFiller =
  FieldFiller;
