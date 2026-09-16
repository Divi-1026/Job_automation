// ============================================================
// CareerSync Autofill
// FormScanner.js
//
// Responsibility:
// - Detect fillable fields on a webpage
// - Extract useful labels/context
// - Support input, textarea, select, radio and checkbox
// - Ignore hidden/disabled/non-form controls
// - Leave legal consent/privacy/declaration decisions to the user
// ============================================================

class FormScanner {
  constructor() {
    this.supportedTags = [
      "INPUT",
      "TEXTAREA",
      "SELECT"
    ];

    this.ignoredInputTypes = new Set([
      "hidden",
      "submit",
      "button",
      "reset",
      "image",
      "file",
      "password"
    ]);
  }

  scan(root = document) {
    const elements = root.querySelectorAll(
      "input, textarea, select"
    );

    const fields = [];

    elements.forEach((element) => {
      if (!this.isFillable(element)) {
        return;
      }

      const field =
        this.buildFieldInfo(element);

      if (!field) {
        return;
      }

      if (
        this.isUserDecisionOnlyField(field)
      ) {
        console.log(
          `[CareerSync][Scanner] User-only decision left untouched: "${field.label}"`
        );

        return;
      }

      fields.push(field);
    });

    console.log(
      `[CareerSync] FormScanner found ${fields.length} fillable field(s).`
    );

    return fields;
  }

  isFillable(element) {
    if (!element) return false;

    if (
      !this.supportedTags.includes(
        element.tagName
      )
    ) {
      return false;
    }

    if (
      element.disabled ||
      element.readOnly
    ) {
      return false;
    }

    if (
      element.tagName === "INPUT"
    ) {
      const type = (
        element.getAttribute("type") ||
        "text"
      ).toLowerCase();

      if (
        this.ignoredInputTypes.has(type)
      ) {
        return false;
      }
    }

    return true;
  }

  buildFieldInfo(element) {
    const label =
      this.getBestLabel(element);

    const type =
      element.tagName === "INPUT"
        ? (element.type || "text").toLowerCase()
        : element.tagName.toLowerCase();

    return {
      element,
      tagName:
        element.tagName.toLowerCase(),
      type,
      label,
      normalizedLabel:
        this.normalizeText(label),
      name:
        element.getAttribute("name") || "",
      id:
        element.id || "",
      placeholder:
        element.getAttribute("placeholder") || "",
      ariaLabel:
        element.getAttribute("aria-label") || "",
      autocomplete:
        element.getAttribute("autocomplete") || "",
      required:
        element.required ||
        element.getAttribute("aria-required") === "true",
      currentValue:
        this.getCurrentValue(element),
      options:
        this.getOptions(element)
    };
  }

  getBestLabel(element) {
    const candidates = [
      this.getExplicitLabel(element),
      this.getWrappedLabel(element),
      this.getAriaLabel(element),
      this.getAriaLabelledBy(element),
      element.getAttribute("placeholder"),
      this.getNearbyText(element),
      element.getAttribute("name"),
      element.id
    ];

    for (
      const candidate of candidates
    ) {
      const cleaned =
        this.cleanLabel(candidate);

      if (cleaned) {
        return cleaned;
      }
    }

    return "";
  }

  getExplicitLabel(element) {
    if (!element.id) return "";

    try {
      const escapedId =
        CSS.escape(element.id);

      const label =
        document.querySelector(
          `label[for="${escapedId}"]`
        );

      return label
        ? label.innerText ||
            label.textContent ||
            ""
        : "";
    }
    catch (error) {
      return "";
    }
  }

  getWrappedLabel(element) {
    const label =
      element.closest("label");

    if (!label) return "";

    return (
      label.innerText ||
      label.textContent ||
      ""
    );
  }

  getAriaLabel(element) {
    return (
      element.getAttribute("aria-label") ||
      ""
    );
  }

  getAriaLabelledBy(element) {
    const labelledBy =
      element.getAttribute(
        "aria-labelledby"
      );

    if (!labelledBy) {
      return "";
    }

    return labelledBy
      .split(/\s+/)
      .filter(Boolean)
      .map(id => {
        const node =
          document.getElementById(id);

        return node
          ? node.innerText ||
              node.textContent ||
              ""
          : "";
      })
      .filter(Boolean)
      .join(" ");
  }

  getNearbyText(element) {
    const containers = [
      element.parentElement,
      element.parentElement?.parentElement,
      element.closest(
        ".form-group, .field, .form-field, .input-group, .question, [role='group']"
      )
    ].filter(Boolean);

    for (
      const container of containers
    ) {
      const label =
        container.querySelector(
          "label, legend, .label, .field-label, .question-label"
        );

      if (
        label &&
        label !== element
      ) {
        const text =
          label.innerText ||
          label.textContent ||
          "";

        if (text.trim()) {
          return text;
        }
      }
    }

    return "";
  }

  getCurrentValue(element) {
    if (
      element.type === "checkbox" ||
      element.type === "radio"
    ) {
      return element.checked
        ? element.value || true
        : "";
    }

    return element.value || "";
  }

  getOptions(element) {
    if (
      element.tagName !== "SELECT"
    ) {
      return [];
    }

    return Array.from(
      element.options
    ).map(option => ({
      text:
        (option.textContent || "").trim(),
      value:
        option.value,
      disabled:
        option.disabled
    }));
  }

  getDecisionContext(field) {
    const element =
      field?.element;

    const pieces = [
      field?.label,
      field?.name,
      field?.id,
      field?.placeholder,
      field?.ariaLabel
    ];

    const container =
      element?.closest(
        "label, fieldset, .form-group, .field, .form-field, .question, [role='group']"
      );

    if (container) {
      pieces.push(
        container.innerText ||
        container.textContent ||
        ""
      );
    }

    return this.normalizeText(
      pieces
        .filter(Boolean)
        .join(" ")
    );
  }

  isUserDecisionOnlyField(field) {
    const text =
      this.getDecisionContext(field);

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

  cleanLabel(value) {
    if (!value) return "";

    return String(value)
      .replace(/\*/g, " ")
      .replace(/\s+/g, " ")
      .trim();
  }

  normalizeText(value) {
    if (!value) return "";

    return String(value)
      .toLowerCase()
      .replace(/[_-]+/g, " ")
      .replace(/[^\w\s]/g, " ")
      .replace(/\s+/g, " ")
      .trim();
  }
}

window.CareerSyncFormScanner =
  FormScanner;
