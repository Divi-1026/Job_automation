// ============================================================
// CareerSync Autofill
// content.js
//
// FINAL FLOW
// 1. Detect every fillable field
// 2. Layer 1: exact learned/custom answer (offline)
// 3. Layer 2: canonical profile + pattern/fuzzy matching (offline)
// 4. Layer 3: AI semantic match ONLY for unresolved fields
// 5. Ask user only when all matching layers fail; save for next time
// ============================================================

(() => {
  console.log("[CareerSync] PRODUCTION UNIVERSAL v3.1.0 loaded:", window.location.href);

  const FormScanner = window.CareerSyncFormScanner;
  const FieldFiller = window.CareerSyncFieldFiller;
  const DOMObserver = window.CareerSyncDOMObserver;
  const ConfidenceUI = window.CareerSyncConfidenceUI;

  if (!FormScanner || !FieldFiller || !DOMObserver || !ConfidenceUI) {
    console.error("[CareerSync] Required modules missing.", {
      FormScanner: !!FormScanner,
      FieldFiller: !!FieldFiller,
      DOMObserver: !!DOMObserver,
      ConfidenceUI: !!ConfidenceUI
    });
    return;
  }

  const scanner = new FormScanner();
  const filler = new FieldFiller();
  const confidenceUI = new ConfidenceUI();

  let cachedProfile = null;
  let cachedMemory = null;
  let autofillRunning = false;
  let dynamicRestartDepth = 0;

  // ============================================================
  // BASIC HELPERS
  // ============================================================

  function normalize(value) {
    return String(value || "")
      .toLowerCase()
      .replace(/[_-]+/g, " ")
      .replace(/[^\w\s]/g, " ")
      .replace(/\s+/g, " ")
      .trim();
  }

  function isEmpty(value) {
    return (
      value === null ||
      value === undefined ||
      String(value).trim() === ""
    );
  }

  function getElement(field) {
    return (
      field?.element ||
      field?.el ||
      field?.node ||
      field?.input ||
      null
    );
  }

  function safeEscape(value) {
    const text = String(value || "");
    if (window.CSS?.escape) {
      return CSS.escape(text);
    }
    return text.replace(/["\\]/g, "\\$&");
  }

  // ============================================================
  // READ REAL FIELD INFORMATION DIRECTLY FROM THE DOM
  //
  // This is important because different scanners / websites may
  // return different metadata even though the actual DOM element
  // is perfectly usable.
  // ============================================================

  function cleanLabelText(node) {
    if (!node) return "";

    // IMPORTANT: label.textContent on many ATS pages includes the entire
    // <select> option list. Clone the label and remove interactive controls
    // before reading its text so a question such as "What is your location?"
    // does not become "What is your location? Afghanistan Albania ...".
    const clone = node.cloneNode(true);

    clone.querySelectorAll(
      "select, option, input, textarea, button, datalist, script, style, svg"
    ).forEach(child => child.remove());

    return String(clone.textContent || "")
      .replace(/\s+/g, " ")
      .replace(/\s*\*\s*$/, "")
      .trim()
      .slice(0, 240);
  }

  function getDomLabel(element) {
    if (!element) return "";

    // 1. Explicit <label for="...">
    if (element.id) {
      const label = document.querySelector(
        `label[for="${safeEscape(element.id)}"]`
      );

      const text = cleanLabelText(label);
      if (text) return text;
    }

    // 2. aria-label (usually cleaner than a wrapped label)
    const ariaLabel = String(
      element.getAttribute("aria-label") || ""
    ).replace(/\s+/g, " ").trim();

    if (ariaLabel) {
      return ariaLabel.slice(0, 240);
    }

    // 3. aria-labelledby
    const labelledBy = element.getAttribute("aria-labelledby");

    if (labelledBy) {
      const text = labelledBy
        .split(/\s+/)
        .map(id => cleanLabelText(document.getElementById(id)))
        .filter(Boolean)
        .join(" ")
        .replace(/\s+/g, " ")
        .trim();

      if (text) return text.slice(0, 240);
    }

    // 4. Element wrapped by label. Remove the input/select itself first.
    const wrappedLabel = element.closest("label");
    const wrappedText = cleanLabelText(wrappedLabel);

    if (wrappedText) {
      return wrappedText;
    }

    // 5. Previous sibling label / text
    const previous = element.previousElementSibling;

    if (previous) {
      const previousText = cleanLabelText(previous);

      if (previousText && previousText.length <= 180) {
        return previousText;
      }
    }

    // 6. Nearest field container containing a label
    let parent = element.parentElement;

    for (let depth = 0; parent && depth < 4; depth++, parent = parent.parentElement) {
      const label = parent.querySelector(":scope > label");
      const text = cleanLabelText(label);

      if (text) {
        return text;
      }
    }

    return "";
  }

  function enrichField(originalField) {
    const element = getElement(originalField);

    if (!element) {
      return {
        ...originalField,
        element: null
      };
    }

    const domLabel = getDomLabel(element);

    // ATS widgets such as HirePro <hp-ta-dropdown> expose the editable part
    // as a normal text input. Treat that INPUT itself as the logical custom
    // select so profile values are selected from the widget, not merely typed.
    let resolvedType = originalField?.type || String(element.type || element.tagName || "").toLowerCase();
    if (element.matches?.('input[aria-autocomplete="list"], input[role="combobox"]') || element.closest?.('hp-ta-dropdown')) {
      resolvedType = "custom-select";
    }

    return {
      ...originalField,

      element,
      type: resolvedType,

      label:
        originalField?.label ||
        domLabel ||
        "",

      name:
        originalField?.name ||
        element.name ||
        "",

      id:
        originalField?.id ||
        element.id ||
        "",

      placeholder:
        originalField?.placeholder ||
        element.getAttribute("placeholder") ||
        "",

      ariaLabel:
        originalField?.ariaLabel ||
        element.getAttribute("aria-label") ||
        "",

      autocomplete:
        originalField?.autocomplete ||
        element.getAttribute("autocomplete") ||
        "",

      required:
        Boolean(
          originalField?.required ||
          element.required ||
          element.getAttribute("aria-required") === "true"
        ),

      type:
        element.tagName?.toLowerCase() === "select"
          ? "select"
          : (
              originalField?.type ||
              element.type ||
              element.tagName ||
              ""
            ).toLowerCase()
    };
  }

  function getGroupContainer(element) {
    if (!element) return null;

    return (
      element.closest("fieldset") ||
      element.closest('[role="radiogroup"]') ||
      element.closest('[role="group"]') ||
      element.closest(".application-question") ||
      element.closest(".field") ||
      null
    );
  }

  function getGroupQuestion(element) {
    const container = getGroupContainer(element);
    if (!container) return "";

    const candidates = [];

    const legend = container.querySelector(":scope > legend, legend");
    if (legend?.textContent?.trim()) candidates.push(legend.textContent.trim());

    const labelledBy = container.getAttribute("aria-labelledby");
    if (labelledBy) {
      const text = labelledBy
        .split(/\s+/)
        .map(id => document.getElementById(id)?.textContent?.trim() || "")
        .filter(Boolean)
        .join(" ");
      if (text) candidates.push(text);
    }

    const ownAria = container.getAttribute("aria-label");
    if (ownAria?.trim()) candidates.push(ownAria.trim());

    for (const selector of [
      ":scope > label",
      ":scope > .label",
      ":scope > .question",
      ":scope > .application-label",
      "h1", "h2", "h3", "h4", "h5", "h6"
    ]) {
      const node = container.querySelector(selector);
      if (node?.textContent?.trim()) candidates.push(node.textContent.trim());
    }

    const optionLabel = normalize(getDomLabel(element));

    for (const candidate of candidates) {
      const text = String(candidate || "").replace(/\s+/g, " ").trim();
      if (!text || text.length > 240) continue;

      // Do not mistake the option text itself for the group question.
      if (normalize(text) === optionLabel) continue;

      return text;
    }

    return "";
  }

  function getRadioGroupElements(element) {
    if (!element) return [];

    if (element.name) {
      const byName = Array.from(
        document.querySelectorAll(
          `input[type="radio"][name="${safeEscape(element.name)}"]`
        )
      );
      if (byName.length > 1) return byName;
    }

    const container = getGroupContainer(element);
    if (container) {
      const grouped = Array.from(
        container.querySelectorAll('input[type="radio"]')
      );
      if (grouped.length > 1) return grouped;
    }

    return [element];
  }

  function getDetectedFieldKey(field) {
    const element = getElement(field);
    const type = getElementType(field);

    if (type === "radio") {
      const radios = getRadioGroupElements(element);
      if (radios.length > 1) {
        const container = getGroupContainer(element);
        return [
          "radio-group",
          element?.name || "",
          container?.id || "",
          normalize(getGroupQuestion(element))
        ].join(":");
      }
    }

    return [
      type,
      element?.name || "",
      element?.id || "",
      normalize(getDomLabel(element))
    ].join(":");
  }

  function scanFields() {
    const rawFields = scanner.scan() || [];

    // Universal discovery for SPA/custom form controls. Native controls come
    // from FormScanner; this layer covers React/Radix/HeadlessUI/MUI/Angular.
    const customSeen = new Set(rawFields.map(f => getElement(f)).filter(Boolean));
    const candidates = Array.from(document.querySelectorAll([
      '[role="combobox"]','[role="textbox"]','[contenteditable="true"]',
      'input[aria-autocomplete="list"]','hp-ta-dropdown input[type="text"]',
      'button[aria-haspopup="listbox"]','button[aria-haspopup="menu"]',
      'button[aria-haspopup="dialog"]','[data-radix-select-trigger]','button'
    ].join(',')));

    for (const element of candidates) {
      if (customSeen.has(element) || element.disabled || !element.getClientRects().length) continue;

      let nearbyLabel = '';
      let parent = element.parentElement;
      for (let depth=0; parent && depth<5; depth++, parent=parent.parentElement) {
        const labelNode = parent.querySelector(':scope > label, :scope > legend, :scope > [class*="label"], :scope > [class*="Label"]');
        const txt = cleanLabelText(labelNode);
        if (txt) { nearbyLabel=txt; break; }
      }

      const ownText=String(element.innerText||element.textContent||'').replace(/\s+/g,' ').trim().slice(0,240);
      const label=getDomLabel(element)||nearbyLabel||element.getAttribute('aria-label')||element.getAttribute('placeholder')||ownText||element.getAttribute('name')||element.id||'';
      const context=normalize([label,ownText,element.getAttribute('name'),element.id,element.getAttribute('aria-label'),element.getAttribute('placeholder')].filter(Boolean).join(' '));

      if (/\b(password|passcode|confirm password|new password)\b/.test(context)) continue;
      if (/\b(choose file|upload file|attach file|resume upload|cv upload)\b/.test(context)) continue;
      if (/\b(i agree|consent|privacy policy|privacy notice|terms(?: and conditions| of use| of service)?|i declare|declaration|i acknowledge|acknowledgement|authorization|authorisation|i certify|certification|electronic signature|personal data|data processing)\b/.test(context)) continue;

      const role=normalize(element.getAttribute('role'));
      const popup=normalize(element.getAttribute('aria-haspopup'));
      let type='';
      if ((element.matches?.('hp-ta-dropdown input[type="text"]') || element.getAttribute('aria-autocomplete')==='list') && /\b(degree|college|branch|education|qualification|course|specialization|specialisation|major|institute|university|location|city|state|country)\b/.test(context)) type='custom-select';
      else if (element.getAttribute('contenteditable')==='true' || role==='textbox') type='richtext';
      else if (popup==='dialog' && /\b(date|dob|birth|joining|start|end|available|availability|current date|today)\b/.test(context)) type='custom-date';
      else {
        const fieldButton=element.tagName==='BUTTON' && nearbyLabel &&
          !/\b(submit|next|previous|back|continue|apply|save|cancel|close|login|sign in|register|upload|add|remove|view)\b/.test(context) &&
          (/\b(select|choose|degree|college|branch|education|year|passing|location|gender|category|country|state|city|course|qualification|cgpa|percentage|experience|notice period)\b/.test(context) || popup==='listbox' || popup==='menu');
        if (role==='combobox'||popup==='listbox'||popup==='menu'||element.hasAttribute('data-radix-select-trigger')||fieldButton) type='custom-select';
      }
      if (!type) continue;
      rawFields.push({element,type,label,name:element.getAttribute('name')||'',id:element.id||'',placeholder:element.getAttribute('placeholder')||'',ariaLabel:element.getAttribute('aria-label')||'',autocomplete:element.getAttribute('autocomplete')||'',required:element.getAttribute('aria-required')==='true'});
      customSeen.add(element);
    }

    const enriched = rawFields
      .map(enrichField)
      .filter(field => !!field.element);

    // Process an exclusive radio group ONCE as one logical question.
    // This prevents options such as "Bachelor" and "Masters" from being
    // treated as two separate questions when they belong to one group.
    const fields = [];
    const seen = new Set();

    for (const field of enriched) {
      const key = getDetectedFieldKey(field);
      if (seen.has(key)) continue;
      seen.add(key);
      fields.push(field);
    }

    console.log(
      `[CareerSync] Enriched ${enriched.length}/${rawFields.length} detected field(s); ${fields.length} logical field/group(s) after radio dedupe.`
    );

    return fields;
  }

  function getQuestion(field) {
    const element = getElement(field);
    const domLabel = getDomLabel(element);
    const type = getElementType(field);

    // For radio groups use the group question/legend rather than an individual
    // option label. For checkboxes keep BOTH the group question and option
    // label, e.g. "Pronouns: She/her" or "Race/Ethnicity: Asian".
    const groupQuestion =
      (type === "radio" || type === "checkbox")
        ? getGroupQuestion(element)
        : "";

    if (
      type === "checkbox" &&
      groupQuestion &&
      domLabel &&
      normalize(groupQuestion) !== normalize(domLabel)
    ) {
      const composite = `${groupQuestion}: ${domLabel}`
        .replace(/\s+/g, " ")
        .trim();

      if (composite.length <= 240) {
        return composite;
      }
    }

    // Prefer the cleaned DOM label. Scanner labels on ATS pages can contain
    // every dropdown option and are therefore unsafe as the primary question.
    const candidates = [
      groupQuestion,
      domLabel,
      field?.ariaLabel,
      element?.getAttribute("aria-label"),
      field?.placeholder,
      element?.getAttribute("placeholder"),
      field?.label,
      field?.name,
      element?.name,
      field?.id,
      element?.id,
      "This field"
    ];

    for (const candidate of candidates) {
      const text = String(candidate || "")
        .replace(/\s+/g, " ")
        .trim();

      // Reject scanner text polluted by a large option list.
      if (text && text.length <= 240) {
        return text;
      }
    }

    return "This field";
  }

  function getFieldContext(field) {
    const element = getElement(field);

    const safeScannerLabel =
      String(field?.label || "").trim().length <= 240
        ? field?.label
        : "";

    const parts = [
      getQuestion(field),
      safeScannerLabel,
      getDomLabel(element),
      field?.name,
      element?.name,
      field?.id,
      element?.id,
      field?.placeholder,
      element?.getAttribute("placeholder"),
      field?.ariaLabel,
      element?.getAttribute("aria-label"),
      field?.autocomplete,
      element?.getAttribute("autocomplete")
    ];

    return normalize(
      [...new Set(parts.filter(Boolean))]
        .join(" ")
    );
  }

  function getElementType(field) {
    const element = getElement(field);

    if (!element) return "";

    if (element.tagName?.toLowerCase() === "select") {
      return "select";
    }

    if (element.tagName?.toLowerCase() === "textarea") {
      return "textarea";
    }

    return String(
      field?.type ||
      element.type ||
      element.tagName ||
      ""
    ).toLowerCase();
  }

  // ============================================================
  // USER-ONLY DECISION / CONSENT GUARD
  //
  // CareerSync must leave legal consent, privacy, declaration,
  // acknowledgement and authorization decisions untouched.
  // They are not sent to memory, profile matching, AI or popup.
  // ============================================================

  function isUserDecisionOnlyField(field) {
    const element = getElement(field);

    if (!element) {
      return false;
    }

    const question = normalize(
      getQuestion(field)
    );

    const context = normalize(
      getFieldContext(field)
    );

    const text =
      `${question} ${context}`;

    const patterns = [
      /\bi agree\b/,
      /\bi consent\b/,
      /\bconsent\b/,
      /\bvoluntarily consent\b/,
      /\bgive my consent\b/,
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
      /\bauthorisation\b/,
      /\bauthorization\b/,
      /\bi declare\b/,
      /\bdeclaration\b/,
      /\bi certify\b/,
      /\bcertify that\b/,
      /\bcertification\b/,
      /\bpersonal data\b/,
      /\bdata processing\b/,
      /\bprocessing my data\b/,
      /\bprocessing of my data\b/,
      /\bcollecting my data\b/,
      /\blegally binding\b/,
      /\belectronic signature\b/,
      /\bbackground check consent\b/
    ];

    return patterns.some(
      pattern => pattern.test(text)
    );
  }


  function isAnswerableField(field) {
    const element = getElement(field);

    if (!element) {
      return false;
    }

    const type = getElementType(field);

    if (
      [
        "hidden",
        "submit",
        "button",
        "reset",
        "image",
        "file",
        "password"
      ].includes(type)
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
      isUserDecisionOnlyField(field)
    ) {
      console.log(
        `[CareerSync][USER ACTION REQUIRED] Leaving untouched: "${getQuestion(field)}"`
      );

      return false;
    }

    return true;
  }

  function currentFieldHasValue(field) {
    const element = getElement(field);

    if (!element) return false;

    const type = getElementType(field);

    if (type === "custom-select" || type === "custom-date") {
      const text=normalize(element.innerText||element.textContent||'');
      return Boolean(text && !/^(select|choose|pick)\b/.test(text) && !/\b(select|choose|pick)\s+(degree|college|branch|date|year|option)\b/.test(text));
    }

    if (type === "checkbox") {
      return Boolean(element.checked);
    }

    if (type === "custom-date") {
      const text =
        normalize(
          element.innerText ||
          element.textContent ||
          ""
        );

      return (
        text &&
        !/\b(select|choose|pick)\b/.test(text)
      );
    }

    if (type === "radio") {
      if (!element.name) {
        return Boolean(element.checked);
      }

      return Boolean(
        document.querySelector(
          `input[type="radio"][name="${safeEscape(element.name)}"]:checked`
        )
      );
    }

    return !isEmpty(element.value);
  }

  // ============================================================
  // BACKEND COMMUNICATION
  // ============================================================

  async function getProfile(forceRefresh = false) {
    if (
      cachedProfile &&
      !forceRefresh
    ) {
      return cachedProfile;
    }

    const response =
      await chrome.runtime.sendMessage({
        type: "CAREERSYNC_GET_PROFILE"
      });

    if (!response?.success) {
      throw new Error(
        response?.error ||
        "Could not load CareerSync profile."
      );
    }

    // Supports both:
    // { success:true, profile:{ personalInfo:... } }
    // and a possible extra nested { profile:{ profile:{...} } }
    const rawProfile =
      response.profile || {};

    cachedProfile =
      rawProfile.profile ||
      rawProfile;

    console.log(
      "[CareerSync] Profile loaded:",
      {
        fullName:
          cachedProfile?.personalInfo?.fullName,
        email:
          cachedProfile?.personalInfo?.email,
        phone:
          cachedProfile?.personalInfo?.phone,
        college:
          cachedProfile?.education?.college,
        skillCount:
          cachedProfile?.professional?.skills?.length || 0
      }
    );

    return cachedProfile;
  }

  async function getMemory(forceRefresh = false) {
    if (
      cachedMemory &&
      !forceRefresh
    ) {
      return cachedMemory;
    }

    const response =
      await chrome.runtime.sendMessage({
        type: "CAREERSYNC_GET_MEMORY"
      });

    if (!response?.success) {
      throw new Error(
        response?.error ||
        "Could not load CareerSync memory."
      );
    }

    cachedMemory =
      Array.isArray(response.items)
        ? response.items
        : Array.isArray(response.memory)
          ? response.memory
          : Array.isArray(response.memories)
            ? response.memories
            : [];

    cachedMemory = cachedMemory.filter(memory => {
      const t=normalize(`${memory?.question||''} ${memory?.normalizedQuestion||memory?.normalized_question||''}`);
      return !/\b(i agree|consent|privacy policy|privacy notice|terms|i declare|declaration|i acknowledge|acknowledgement|authorization|authorisation|i certify|certification|electronic signature|personal data|data processing)\b/.test(t);
    });

    console.log(
      `[CareerSync] Loaded ${cachedMemory.length} learned answer(s).`
    );

    return cachedMemory;
  }

  async function saveMemory({
    question,
    answer,
    field,
    source = "manual",
    confidence = 1
  }) {
    if (isUserDecisionOnlyField(field) || getElementType(field) === "password") {
      console.log(`[CareerSync][MEMORY BLOCKED] "${getQuestion(field)}".`);
      return { success: false, blocked: true };
    }

    const element =
      getElement(field);

    const response =
      await chrome.runtime.sendMessage({
        type:
          "CAREERSYNC_SAVE_MEMORY",

        payload: {
          question,

          answer:
            String(answer),

          field_context: {
            label:
              getQuestion(field),

            name:
              field?.name ||
              element?.name ||
              "",

            id:
              field?.id ||
              element?.id ||
              "",

            type:
              getElementType(field),

            tagName:
              element?.tagName ||
              "",

            placeholder:
              field?.placeholder ||
              element?.getAttribute("placeholder") ||
              "",

            ariaLabel:
              field?.ariaLabel ||
              element?.getAttribute("aria-label") ||
              "",

            autocomplete:
              field?.autocomplete ||
              element?.getAttribute("autocomplete") ||
              "",

            required:
              Boolean(
                field?.required ||
                element?.required
              ),

            pageUrl:
              window.location.href,

            pageTitle:
              document.title
          },

          source:
            source,

          confidence:
            confidence
        }
      });

    if (!response?.success) {
      throw new Error(
        response?.error ||
        "Could not save learned answer."
      );
    }

    await getMemory(true);

    return response;
  }

  // ============================================================
  // EXTENSION PROFILE - UPDATE CANONICAL FIELD
  // ============================================================

  async function updateExtensionProfile(
    key,
    value
  ) {
    const response =
      await chrome.runtime.sendMessage({
        type:
          "CAREERSYNC_UPDATE_EXTENSION_PROFILE",

        payload: {
          key,
          value
        }
      });

    if (!response?.success) {
      throw new Error(
        response?.error ||
        "Could not update CareerSync extension profile."
      );
    }

    // Refresh the profile cache so the newly learned canonical
    // value is immediately available during future autofill runs.
    await getProfile(true);

    return response;
  }


  // ============================================================
  // AI ASSISTANT - SEMANTIC FALLBACK
  // ============================================================

  function buildAIFieldPayload(
    item,
    index
  ) {
    const field =
      item?.field || item;

    const profileMatch =
      item?.profileMatch || null;

    const element =
      getElement(field);

    return {
      index,

      question:
        getQuestion(field),

      profile_key:
        profileMatch?.key || null,

      choices:
        getFieldChoices(field),

      field_context: {
        context:
          getFieldContext(field),

        name:
          field?.name ||
          element?.name ||
          "",

        id:
          field?.id ||
          element?.id ||
          "",

        type:
          getElementType(field),

        placeholder:
          field?.placeholder ||
          element?.getAttribute("placeholder") ||
          "",

        ariaLabel:
          field?.ariaLabel ||
          element?.getAttribute("aria-label") ||
          "",

        autocomplete:
          field?.autocomplete ||
          element?.getAttribute("autocomplete") ||
          "",

        pageTitle:
          document.title,

        pageUrl:
          window.location.href
      }
    };
  }


  async function getAISuggestions(
    items
  ) {
    if (!items?.length) {
      return [];
    }

    // Real ATS forms can contain dozens of fields. Send them in small
    // semantic batches so one large provider request cannot fail the
    // entire autofill run. Every unresolved field is still checked by AI.
    const BATCH_SIZE = 8;
    const allResults = [];

    for (
      let offset = 0;
      offset < items.length;
      offset += BATCH_SIZE
    ) {
      const chunk =
        items.slice(
          offset,
          offset + BATCH_SIZE
        );

      const fields =
        chunk.map(
          (item, localIndex) => {
            const payload =
              buildAIFieldPayload(
                item,
                offset + localIndex
              );

            // Keep the global index so results map back to the original
            // unknown-field array across multiple AI batches.
            payload.index =
              offset + localIndex;

            return payload;
          }
        );

      const aiPayload = { fields };
      console.group(`[CareerSync][AI DEBUG] Batch ${Math.floor(offset / BATCH_SIZE) + 1}`);
      console.log("[CareerSync][AI REQUEST]", JSON.parse(JSON.stringify(aiPayload)));

      const response =
        await chrome.runtime.sendMessage({
          type:
            "CAREERSYNC_AI_SUGGEST_BATCH",

          payload: aiPayload
        });
      console.log("[CareerSync][AI BACKEND RESPONSE]", response);
      console.groupEnd();

      if (!response?.success) {
        throw new Error(
          response?.error ||
          `CareerSync AI assistant failed for semantic batch ${Math.floor(offset / BATCH_SIZE) + 1}.`
        );
      }

      const results =
        response?.data?.results;

      if (Array.isArray(results)) {
        console.log("[CareerSync][AI PARSED RESULTS]", results);
        allResults.push(
          ...results
        );
      }
    }

    return allResults;
  }

  // ============================================================
  // CAREERSYNC PROFILE -> COMMON VALUES
  // ============================================================

  function buildProfileValues(profile) {
    const personal =
      profile?.personalInfo || {};

    const education =
      profile?.education || {};

    const professional =
      profile?.professional || {};

    const preferences =
      profile?.preferences || {};

    const fullName =
      personal.fullName || "";

    const nameParts =
      String(fullName)
        .trim()
        .split(/\s+/)
        .filter(Boolean);

    return {
      fullName,

      firstName:
        personal.firstName ||
        nameParts[0] ||
        "",

      lastName:
        personal.lastName ||
        (
          nameParts.length > 1
            ? nameParts.slice(1).join(" ")
            : ""
        ),

      email:
        personal.email || "",

      phone:
        personal.phone || "",

      linkedin:
        personal.linkedIn ||
        personal.linkedin ||
        "",

      github:
        personal.github || "",

      portfolio:
        personal.portfolio || "",

      location:
        personal.location || "",

      address:
        personal.address || "",

      city:
        personal.city ||
        personal.location ||
        "",

      state:
        personal.state || "",

      country:
        personal.country || "",

      pincode:
        personal.pincode || "",

      dateOfBirth:
        personal.dateOfBirth ||
        personal.dob ||
        "",

      gender:
        personal.gender || "",

      highestEducation:
        education.highestEducation || "",

      college:
        education.college || "",

      graduationYear:
        education.graduationYear || "",

      degree:
        education.degree || "",

      branch:
        education.branch || "",

      cgpa:
        education.cgpa || "",

      percentage:
        education.percentage || "",

      class10Percentage:
        education.class10Percentage || "",

      class12Percentage:
        education.class12Percentage || "",

      experienceType:
        professional.experienceType || "",

      yearsOfExperience:
        professional.yearsOfExperience ?? "",

      currentCompany:
        professional.currentCompany || "",

      currentRole:
        professional.currentRole || "",

      skills:
        Array.isArray(professional.skills)
          ? professional.skills.join(", ")
          : professional.skills || "",

      bio:
        professional.bio || "",

      preferredRoles:
        Array.isArray(
          preferences.preferredRoles?.length
            ? preferences.preferredRoles
            : professional.preferredRoles
        )
          ? (
              preferences.preferredRoles?.length
                ? preferences.preferredRoles
                : professional.preferredRoles
            ).join(", ")
          : (
              preferences.preferredRoles ||
              professional.preferredRoles ||
              ""
            ),

      preferredLocations:
        Array.isArray(preferences.preferredLocations)
          ? preferences.preferredLocations.join(", ")
          : preferences.preferredLocations || "",

      expectedCTC:
        preferences.expectedCTC || "",

      noticePeriod:
        preferences.noticePeriod || "",

      willingToRelocate:
        preferences.willingToRelocate ?? ""
    };
  }

  // ============================================================
  // PROFILE FIELD MATCHING
  // ============================================================

  function looksLikeCountrySelect(field) {
    const element = getElement(field);
    if (!element || getElementType(field) !== "select") return false;

    const optionTexts = new Set(
      Array.from(element.options || [])
        .map(option => normalize(option.textContent || option.label || option.value))
        .filter(Boolean)
    );

    if (optionTexts.size < 12) return false;

    const countrySignals = [
      "india",
      "united states",
      "united kingdom",
      "canada",
      "australia",
      "germany",
      "france",
      "japan"
    ];

    let hits = 0;
    for (const signal of countrySignals) {
      if (optionTexts.has(signal)) hits++;
    }

    return hits >= 3;
  }

  function matchField(field, values) {
    const context =
      getFieldContext(field);

    if (!context) {
      return null;
    }

    const result = (
      key,
      value,
      confidence = 0.95
    ) => ({
      key,
      value,
      confidence
    });

    // ---------- Name ----------

    if (
      /\b(first name|firstname|given name|givenname|fname)\b/.test(context)
    ) {
      return result(
        "firstName",
        values.firstName,
        0.99
      );
    }

    if (
      /\b(last name|lastname|surname|family name|familyname|lname)\b/.test(context)
    ) {
      return result(
        "lastName",
        values.lastName,
        0.99
      );
    }

    if (
      /\b(full name|fullname|full legal name|candidate name|applicant name|your name|legal name)\b/.test(context) ||
      context === "name" ||
      /\bname enter full name\b/.test(context)
    ) {
      return result(
        "fullName",
        values.fullName,
        0.99
      );
    }

    // ---------- Contact ----------

    if (
      getElementType(field) === "email" ||
      /\b(email|e mail|email address|mail id|email id)\b/.test(context)
    ) {
      return result(
        "email",
        values.email,
        0.99
      );
    }

    if (
      getElementType(field) === "tel" ||
      /\b(phone|phone number|mobile|mobile number|contact number|telephone|whatsapp)\b/.test(context)
    ) {
      return result(
        "phone",
        values.phone,
        0.99
      );
    }

    if (
      /\b(linkedin|linked in)\b/.test(context)
    ) {
      return result(
        "linkedin",
        values.linkedin,
        0.99
      );
    }

    if (
      /\b(github|git hub)\b/.test(context)
    ) {
      return result(
        "github",
        values.github,
        0.99
      );
    }

    if (
      /\b(portfolio|personal website|website url|personal site)\b/.test(context)
    ) {
      return result(
        "portfolio",
        values.portfolio,
        0.96
      );
    }

    if (
      /\b(date of birth|birth date|dob)\b/.test(context)
    ) {
      return result(
        "dateOfBirth",
        values.dateOfBirth,
        0.98
      );
    }

    if (
      /\b(gender|sex)\b/.test(context)
    ) {
      return result(
        "gender",
        values.gender,
        0.97
      );
    }

    // ---------- Address ----------

    // Specific postal fields must win over generic address matching.
    if (/\b(pin code|pincode|postal code|zip code|zipcode)\b/.test(context)) {
      return result("pincode", values.pincode, 0.99);
    }

    if (
      /\b(current address|residential address|address)\b/.test(context)
    ) {
      return result(
        "address",
        values.address,
        0.94
      );
    }

    if (
      /\b(current city|residing city|city)\b/.test(context)
    ) {
      return result(
        "city",
        values.city,
        0.95
      );
    }

    if (
      /\b(current location|location)\b/.test(context) &&
      !/\bpreferred\b/.test(context) &&
      looksLikeCountrySelect(field)
    ) {
      return result(
        "country",
        values.country,
        0.97
      );
    }

    if (
      /\b(current location|location)\b/.test(context) &&
      !/\bpreferred\b/.test(context)
    ) {
      return result(
        "location",
        values.location,
        0.93
      );
    }

    if (
      /\b(state|province)\b/.test(context)
    ) {
      return result(
        "state",
        values.state,
        0.94
      );
    }

    if (
      /\b(country|nationality)\b/.test(context)
    ) {
      return result(
        "country",
        values.country,
        0.94
      );
    }

    if (
      /\b(pin code|pincode|postal code|zip code|zipcode)\b/.test(context)
    ) {
      return result(
        "pincode",
        values.pincode,
        0.94
      );
    }

    // ---------- Education ----------

    if (
      /\b(class 10|class x|10th|tenth)\b/.test(context) &&
      /\b(percentage|percent|marks|score)\b/.test(context)
    ) {
      return result(
        "class10Percentage",
        values.class10Percentage,
        0.96
      );
    }

    if (
      /\b(class 12|class xii|12th|twelfth)\b/.test(context) &&
      /\b(percentage|percent|marks|score)\b/.test(context)
    ) {
      return result(
        "class12Percentage",
        values.class12Percentage,
        0.96
      );
    }

    if (
      /\b(college|college name|university|university name|institution|institute)\b/.test(context)
    ) {
      return result(
        "college",
        values.college,
        0.98
      );
    }

    if (
      /\b(graduation year|graduating year|year of graduation|passing year|year of passing|expected graduation|graduation date)\b/.test(context)
    ) {
      return result(
        "graduationYear",
        values.graduationYear,
        0.97
      );
    }

    if (
      /\b(highest education|highest qualification|qualification|education level)\b/.test(context)
    ) {
      return result(
        "highestEducation",
        values.highestEducation,
        0.95
      );
    }

    if (
      /\b(degree)\b/.test(context)
    ) {
      return result(
        "degree",
        values.degree,
        0.95
      );
    }

    if (
      /\b(branch|specialization|specialisation|major|field of study|stream)\b/.test(context)
    ) {
      return result(
        "branch",
        values.branch,
        0.95
      );
    }

    // A "Percentage/CGPA" radio group asks for the grading MODE, not the
    // numeric score. If a CGPA exists in profile, choose CGPA; the numeric
    // input that Angular renders afterwards is handled on the next scan.
    if (getElementType(field) === "radio" && /\bpercentage\b/.test(context) && /\bcgpa\b/.test(context)) {
      return result("scoreType", !isEmpty(values.cgpa) ? "CGPA" : "Percentage", 0.99);
    }

    if (
      /\b(cgpa|gpa|cumulative gpa)\b/.test(context)
    ) {
      return result(
        "cgpa",
        values.cgpa,
        0.97
      );
    }

    // ---------- Professional ----------

    if (
      /\b(experience level|experience type)\b/.test(context)
    ) {
      return result(
        "experienceType",
        values.experienceType,
        0.96
      );
    }

    if (
      /\b(years of experience|total experience|work experience|experience years)\b/.test(context)
    ) {
      return result(
        "yearsOfExperience",
        values.yearsOfExperience,
        0.94
      );
    }

    if (
      /\b(current company|current employer|employer name|recent company|most recent company)\b/.test(context)
    ) {
      return result(
        "currentCompany",
        values.currentCompany,
        0.94
      );
    }

    if (
      /\b(current role|current designation|job title|current title|recent role|most recent role)\b/.test(context)
    ) {
      return result(
        "currentRole",
        values.currentRole,
        0.94
      );
    }

    if (
      /\b(skills|technical skills|key skills|primary skills|technologies known)\b/.test(context)
    ) {
      return result(
        "skills",
        values.skills,
        0.98
      );
    }

    if (
      /\b(bio|about yourself|professional summary|profile summary)\b/.test(context)
    ) {
      return result(
        "bio",
        values.bio,
        0.90
      );
    }

    // ---------- Preferences ----------

    if (
      /\b(preferred role|desired role|preferred position)\b/.test(context)
    ) {
      return result(
        "preferredRoles",
        values.preferredRoles,
        0.92
      );
    }

    if (
      /\b(preferred work location|preferred location|desired location)\b/.test(context)
    ) {
      return result(
        "preferredLocations",
        values.preferredLocations,
        0.92
      );
    }

    if (
      /\b(expected ctc|expected salary|salary expectation|expected annual ctc)\b/.test(context)
    ) {
      return result(
        "expectedCTC",
        values.expectedCTC,
        0.94
      );
    }

    if (
      /\b(notice period|joining notice)\b/.test(context)
    ) {
      return result(
        "noticePeriod",
        values.noticePeriod,
        0.94
      );
    }

    if (
      /\b(willing to relocate|relocate|relocation)\b/.test(context)
    ) {
      return result(
        "willingToRelocate",
        values.willingToRelocate,
        0.96
      );
    }

    return null;
  }

  // ============================================================
  // LEARNED MEMORY MATCHING
  // ============================================================

  function memoryQuestionText(memory) {
    return String(
      memory?.normalizedQuestion ||
      memory?.normalized_question ||
      memory?.question ||
      ""
    );
  }

  function memoryContextText(memory) {
    const fc =
      memory?.fieldContext ||
      memory?.field_context ||
      {};

    return normalize([
      memoryQuestionText(memory),
      memory?.question,
      fc?.label,
      fc?.name,
      fc?.id,
      fc?.placeholder,
      fc?.ariaLabel,
      fc?.aria_label,
      fc?.autocomplete
    ].filter(Boolean).join(" "));
  }

  function canonicalMemoryText(value) {
    return normalize(value)
      .replace(/\bdate of birth\b/g, " dob ")
      .replace(/\bbirth date\b/g, " dob ")
      .replace(/\bdriver s licence\b/g, " driving license ")
      .replace(/\bdriver licence\b/g, " driving license ")
      .replace(/\bdriving licence\b/g, " driving license ")
      .replace(/\blicence\b/g, " license ")
      .replace(/\bspecialisation\b/g, " specialization ")
      .replace(/\bfield of study\b/g, " branch ")
      .replace(/\bmajor\b/g, " branch ")
      .replace(/\bhighest qualification\b/g, " highest education ")
      .replace(/\beducation level\b/g, " highest education ")
      .replace(/\bmobile number\b/g, " phone ")
      .replace(/\bphone number\b/g, " phone ")
      .replace(/\bcontact number\b/g, " phone ")
      .replace(/\be mail\b/g, " email ")
      .replace(/\bfull legal name\b/g, " full name ")
      .replace(/\bgiven name\b/g, " first name ")
      .replace(/\bfamily name\b/g, " last name ")
      .replace(/\bsurname\b/g, " last name ")
      .replace(/\bgraduating year\b/g, " graduation year ")
      .replace(/\byear of graduation\b/g, " graduation year ")
      .replace(/\bcurrent employer\b/g, " current company ")
      .replace(/\bcurrent designation\b/g, " current role ")
      .replace(/\bexpected salary\b/g, " expected ctc ")
      .replace(/\bsalary expectation\b/g, " expected ctc ")
      .replace(/\bwilling to relocate\b/g, " relocation ")
      .replace(/\brelocate\b/g, " relocation ")
      .replace(/\s+/g, " ")
      .trim();
  }

  function tokenSet(value) {
    const stopWords = new Set([
      "a", "an", "the", "your", "you", "please", "enter", "provide",
      "select", "choose", "what", "is", "are", "do", "does", "have",
      "has", "of", "for", "to", "in", "on", "with", "current"
    ]);

    return new Set(
      canonicalMemoryText(value)
        .split(/\s+/)
        .filter(token => token && !stopWords.has(token))
    );
  }

  function tokenSimilarity(a, b) {
    const A = tokenSet(a);
    const B = tokenSet(b);

    if (!A.size || !B.size) return 0;

    let common = 0;
    for (const token of A) {
      if (B.has(token)) common++;
    }

    const overlap = common / Math.min(A.size, B.size);
    const jaccard = common / (A.size + B.size - common);

    return Math.max(overlap, jaccard);
  }

  function findMemoryByProfileKey(profileMatch, memories) {
    if (!profileMatch?.key) return null;

    const aliases = {
      firstName: ["first name", "given name"],
      lastName: ["last name", "surname", "family name"],
      fullName: ["full name", "full legal name", "candidate name", "applicant name"],
      email: ["email", "email address", "email id"],
      phone: ["phone", "phone number", "mobile", "mobile number", "contact number"],
      linkedin: ["linkedin", "linked in"],
      github: ["github", "git hub"],
      portfolio: ["portfolio", "personal website"],
      location: ["current location", "location"],
      address: ["current address", "residential address", "address"],
      city: ["current city", "city"],
      state: ["state", "province"],
      country: ["country", "nationality"],
      pincode: ["pincode", "pin code", "postal code", "zip code"],
      dateOfBirth: ["date of birth", "birth date", "dob"],
      gender: ["gender", "sex"],
      highestEducation: ["highest qualification", "highest education", "qualification", "education level"],
      college: ["college", "college name", "university", "institution", "institute"],
      graduationYear: ["graduation year", "graduating year", "year of graduation", "passing year"],
      degree: ["degree"],
      branch: ["branch", "specialization", "specialisation", "major", "field of study", "stream"],
      cgpa: ["cgpa", "gpa", "cumulative gpa"],
      class10Percentage: ["class 10 percentage", "10th percentage"],
      class12Percentage: ["class 12 percentage", "12th percentage"],
      experienceType: ["experience level", "experience type"],
      yearsOfExperience: ["years of experience", "total experience", "work experience"],
      currentCompany: ["current company", "current employer"],
      currentRole: ["current role", "current designation", "job title"],
      skills: ["skills", "technical skills", "key skills"],
      bio: ["bio", "about yourself", "professional summary", "profile summary"],
      preferredRoles: ["preferred role", "desired role", "preferred position"],
      preferredLocations: ["preferred location", "preferred work location", "desired location"],
      expectedCTC: ["expected ctc", "expected salary", "salary expectation"],
      noticePeriod: ["notice period", "joining notice"],
      willingToRelocate: ["willing to relocate", "relocate", "relocation"]
    };

    const wanted = aliases[profileMatch.key] || [];
    if (!wanted.length) return null;

    let best = null;
    let bestScore = 0;

    for (const memory of memories) {
      const memoryText = canonicalMemoryText(
        `${memoryQuestionText(memory)} ${memoryContextText(memory)}`
      );

      for (const alias of wanted) {
        const canonicalAlias = canonicalMemoryText(alias);

        let score = 0;

        if (memoryText === canonicalAlias) {
          score = 1;
        } else if (
          memoryText.includes(canonicalAlias) ||
          canonicalAlias.includes(memoryText)
        ) {
          score = 0.96;
        } else {
          score = tokenSimilarity(memoryText, canonicalAlias);
        }

        if (score > bestScore) {
          bestScore = score;
          best = memory;
        }
      }
    }

    if (best && bestScore >= 0.90) {
      return {
        answer: best.answer,
        confidence: bestScore,
        memory: best,
        reason: `profile-key:${profileMatch.key}`
      };
    }

    return null;
  }

  // ============================================================
  // LAYER 1: SAVED CUSTOM / LEARNED ANSWER (OFFLINE)
  // Exact normalized question match only. No API call.
  // This mirrors the reference project's Custom Q&A first layer.
  // ============================================================

  function findExactMemoryMatch(field, memories) {
    const question = normalize(getQuestion(field));

    if (!question) return null;

    for (const memory of memories) {
      const memoryQuestion = normalize(memoryQuestionText(memory));

      if (memoryQuestion && memoryQuestion === question && !isEmpty(memory.answer)) {
        return {
          answer: memory.answer,
          confidence: Number(memory.confidence ?? 1),
          memory,
          reason: "exact-question"
        };
      }
    }

    return null;
  }

  function findMemoryMatch(
    field,
    memories,
    profileMatch = null
  ) {
    const question =
      normalize(
        getQuestion(field)
      );

    const context =
      getFieldContext(field);

    if (!question) {
      return null;
    }

    // 1. Exact normalized question.
    for (const memory of memories) {
      const memoryQuestion =
        normalize(
          memoryQuestionText(memory)
        );

      if (
        memoryQuestion &&
        memoryQuestion === question
      ) {
        return {
          answer: memory.answer,
          confidence: Number(memory.confidence ?? 1),
          memory,
          reason: "exact-question"
        };
      }
    }

    // 2. If this form field was recognized as a CareerSync profile field
    // but the canonical profile value is empty, reuse a previously learned
    // answer for that same semantic profile key.
    const profileKeyMemory =
      findMemoryByProfileKey(
        profileMatch,
        memories
      );

    if (profileKeyMemory) {
      return profileKeyMemory;
    }

    // 3. Canonical/similar question matching.
    // This handles small wording changes such as:
    // "Date of Birth" <-> "DOB"
    // "Branch / Specialization" <-> "Branch"
    // "Driving licence?" <-> "Driver's license?"
    const canonicalQuestion =
      canonicalMemoryText(question);

    const canonicalContext =
      canonicalMemoryText(context);

    let best = null;
    let bestScore = 0;

    for (const memory of memories) {
      const memoryQuestion =
        canonicalMemoryText(
          memoryQuestionText(memory)
        );

      const memoryContext =
        canonicalMemoryText(
          memoryContextText(memory)
        );

      if (!memoryQuestion) {
        continue;
      }

      let score = 0;

      if (memoryQuestion === canonicalQuestion) {
        score = 0.99;
      } else if (
        canonicalQuestion.includes(memoryQuestion) ||
        memoryQuestion.includes(canonicalQuestion)
      ) {
        score = 0.95;
      } else {
        score = Math.max(
          tokenSimilarity(canonicalQuestion, memoryQuestion),
          tokenSimilarity(canonicalContext, memoryQuestion),
          tokenSimilarity(canonicalQuestion, memoryContext)
        );
      }

      if (score > bestScore) {
        bestScore = score;
        best = memory;
      }
    }

    // Conservative threshold: auto-fill only when similarity is strong.
    // Otherwise ask the user and learn the new wording.
    if (
      best &&
      bestScore >= 0.88
    ) {
      return {
        answer: best.answer,
        confidence: bestScore,
        memory: best,
        reason: "semantic-question"
      };
    }

    return null;
  }

  // ============================================================
  // FIELD CHOICES
  // ============================================================

  function getRadioLabel(radio) {
    if (!radio) return "";

    if (radio.id) {
      const label =
        document.querySelector(
          `label[for="${safeEscape(radio.id)}"]`
        );

      if (
        label?.textContent?.trim()
      ) {
        return label.textContent.trim();
      }
    }

    const wrapped =
      radio.closest("label");

    if (
      wrapped?.textContent?.trim()
    ) {
      return wrapped.textContent.trim();
    }

    return (
      radio.value ||
      ""
    );
  }

  function getFieldChoices(field) {
    const element =
      getElement(field);

    const type =
      getElementType(field);

    if (!element) {
      return [];
    }

    if (
      type === "select"
    ) {
      return Array.from(
        element.options || []
      )
        .map(option => ({
          value:
            option.value,

          label:
            (
              option.textContent ||
              option.label ||
              option.value ||
              ""
            ).trim()
        }))
        .filter(option =>
          option.label &&
          option.value !== "" &&
          !/^select\b/i.test(option.label) &&
          !/^choose\b/i.test(option.label)
        );
    }

    if (
      type === "radio"
    ) {
      const radios =
        getRadioGroupElements(element);

      return radios
        .map(radio => ({
          value:
            radio.value ||
            getRadioLabel(radio),

          label:
            getRadioLabel(radio) ||
            radio.value ||
            "Option"
        }))
        .filter(choice =>
          String(choice.label || "").trim() ||
          String(choice.value || "").trim()
        );
    }

    if (
      type === "checkbox"
    ) {
      return [
        {
          value: "Yes",
          label: "Yes"
        },
        {
          value: "No",
          label: "No"
        }
      ];
    }

    return [];
  }

  // ============================================================
  // FILL FIELD
  // ============================================================

  function fillSelect(
    element,
    answer
  ) {
    const target =
      normalize(answer);

    if (!target) {
      return false;
    }

    const options =
      Array.from(
        element.options || []
      );

    let matched =
      options.find(option =>
        normalize(option.value) === target
      );

    if (!matched) {
      matched =
        options.find(option =>
          normalize(
            option.textContent
          ) === target
        );
    }

    if (!matched) {
      matched =
        options.find(option => {
          const optionText =
            normalize(
              option.textContent
            );

          return (
            optionText &&
            (
              optionText.includes(target) ||
              target.includes(optionText)
            )
          );
        });
    }

    if (!matched) {
      return false;
    }

    const prototype =
      Object.getPrototypeOf(
        element
      );

    const descriptor =
      Object.getOwnPropertyDescriptor(
        prototype,
        "value"
      );

    if (
      descriptor?.set
    ) {
      descriptor.set.call(
        element,
        matched.value
      );
    }
    else {
      element.value =
        matched.value;
    }

    element.dispatchEvent(
      new Event(
        "input",
        {
          bubbles: true
        }
      )
    );

    element.dispatchEvent(
      new Event(
        "change",
        {
          bubbles: true
        }
      )
    );

    element.dispatchEvent(
      new Event(
        "blur",
        {
          bubbles: true
        }
      )
    );

    element.setAttribute(
      "data-careersync-filled",
      "true"
    );

    return (
      element.value ===
      matched.value
    );
  }

  function coerceAnswerToAllowedChoice(field, answer) {
    const choices = getFieldChoices(field);
    const value = String(answer ?? "").trim();

    if (!choices.length) {
      return value;
    }

    const target = normalize(value);
    if (!target) return null;

    // AI/memory must not inject a profile value that is not one of the form's
    // actual choices. Example: field "Non-binary" must never receive "Female".
    const exact = choices.find(choice =>
      normalize(choice.value) === target ||
      normalize(choice.label) === target
    );

    if (exact) {
      return String(exact.value || exact.label || value).trim();
    }

    return null;
  }

  // ============================================================
  // UNIVERSAL CUSTOM DROPDOWNS
  // ============================================================
  function isCustomSelectField(field) { return getElementType(field)==="custom-select"; }

  function visibleOptionNodes() {
    const selectors=['[role="option"]','[role="menuitem"]','[role="menuitemradio"]','[role="menuitemcheckbox"]','[data-radix-collection-item]','.ng-option','mat-option','[class*="option"]','[class*="Option"]'];
    return Array.from(document.querySelectorAll(selectors.join(','))).filter(el => !el.disabled && el.getAttribute('aria-disabled')!=='true' && el.getClientRects().length && String(el.innerText||el.textContent||'').trim());
  }


  async function getCustomSelectChoices(field) {
    const trigger = getElement(field);
    if (!trigger) return [];
    const before = String(trigger.value ?? trigger.textContent ?? '').trim();
    try {
      const host = trigger.closest('hp-ta-dropdown,.tad-container,.outer-container,[role="combobox"]') || trigger.parentElement;
      const toggle = host?.querySelector('button[dropdown-toggle],[aria-haspopup="listbox"],[aria-haspopup="true"],button');
      (toggle || trigger).click();
      await careerSyncSleep(180);
      let nodes=[];
      for(let i=0;i<20&&!nodes.length;i++){ nodes=visibleOptionNodes(); if(!nodes.length) await careerSyncSleep(60); }
      if(!nodes.length){
        nodes=Array.from(document.querySelectorAll('li,[role="option"],.dropdown-item,.ng-option,mat-option'))
          .filter(el=>el.getClientRects().length && String(el.innerText||el.textContent||'').trim());
      }
      const seen=new Set();
      const choices=[];
      for(const node of nodes){
        const label=String(node.innerText||node.textContent||node.getAttribute('aria-label')||'').replace(/\s+/g,' ').trim();
        if(!label || /^(select|choose)( an? )?(option|answer)?$/i.test(label)) continue;
        const key=normalize(label); if(!key||seen.has(key)) continue; seen.add(key);
        choices.push({value:label,label});
        if(choices.length>=100) break;
      }
      document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',code:'Escape',bubbles:true}));
      trigger.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',code:'Escape',bubbles:true}));
      if (trigger.tagName==='INPUT' && before && trigger.value!==before) {
        const d=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value');
        if(d?.set)d.set.call(trigger,before); else trigger.value=before;
        trigger.dispatchEvent(new Event('input',{bubbles:true}));
      }
      console.log(`[CareerSync][CUSTOM SELECT OPTIONS] "${getQuestion(field)}"`, choices.map(c=>c.label));
      return choices;
    } catch(e){
      console.warn(`[CareerSync][CUSTOM SELECT OPTIONS] Could not read options for "${getQuestion(field)}"`,e);
      return [];
    }
  }

  async function fillCustomSelect(field, answer) {
    const trigger=getElement(field), wanted=String(answer??'').trim();
    if (!trigger || !wanted) return false;
    // Searchable Angular/HirePro controls often expose the text input as the
    // semantic field while a sibling button actually opens the option panel.
    // Focus/type into the input first, then open the sibling toggle when needed.
    trigger.focus?.();
    if (trigger.tagName === 'INPUT') {
      const d=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value');
      if (d?.set) d.set.call(trigger,wanted); else trigger.value=wanted;
      trigger.dispatchEvent(new Event('input',{bubbles:true}));
      trigger.dispatchEvent(new Event('change',{bubbles:true}));
      const host=trigger.closest('hp-ta-dropdown,.tad-container,.outer-container') || trigger.parentElement;
      const toggle=host?.querySelector('button[dropdown-toggle],button,[aria-haspopup="listbox"],[aria-haspopup="true"]');
      (toggle || trigger).click();
    } else {
      trigger.click();
    }
    await careerSyncSleep(220);

    const active=document.activeElement;
    if (active && active!==trigger && (active.tagName==='INPUT'||active.getAttribute('role')==='textbox')) {
      const d=active.tagName==='INPUT'?Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value'):null;
      if (d?.set) d.set.call(active,wanted); else if ('value' in active) active.value=wanted; else active.textContent=wanted;
      active.dispatchEvent(new Event('input',{bubbles:true})); await careerSyncSleep(180);
    }

    let options=[];
    for(let i=0;i<30&&!options.length;i++){ options=visibleOptionNodes(); if(!options.length) await careerSyncSleep(60); }
    if(!options.length) options=Array.from(document.querySelectorAll('li,[tabindex="0"],[tabindex="-1"],button')).filter(el=>el!==trigger&&el.getClientRects().length&&!el.disabled&&String(el.innerText||el.textContent||'').trim());

    const target=normalize(wanted); let best=null,bestScore=0;
    for(const option of options){
      const text=String(option.innerText||option.textContent||option.getAttribute('aria-label')||'').replace(/\s+/g,' ').trim();
      const n=normalize(text); if(!n) continue;
      let score=n===target?1:(n.includes(target)||target.includes(n)?0.95:tokenSimilarity(n,target));
      // Common education aliases.
      const alias=(a,b)=>a.test(n)&&b.test(target)||a.test(target)&&b.test(n);
      if(alias(/b\.?\s*tech|bachelor of technology/,/b\.?\s*tech|bachelor of technology/)) score=Math.max(score,.98);
      if(alias(/information technology|\bit\b/,/information technology|\bit\b/)) score=Math.max(score,.97);
      if(score>bestScore){bestScore=score;best=option;}
    }
    if(!best||bestScore<.70){ document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true})); console.warn(`[CareerSync][CUSTOM SELECT] No safe option for "${getQuestion(field)}" = "${wanted}".`); return false; }
    best.scrollIntoView({block:'nearest'}); best.click(); await careerSyncSleep(140);
    trigger.setAttribute('data-careersync-filled','true');
    console.log(`[CareerSync][CUSTOM SELECT] "${getQuestion(field)}" -> "${String(best.innerText||best.textContent||'').trim()}" (${Math.round(bestScore*100)}%)`);
    return true;
  }

  // ============================================================
  // CUSTOM DATE PICKERS (Radix / button + dialog calendars)
  // ============================================================

  const careerSyncSleep =
    ms => new Promise(
      resolve => setTimeout(resolve, ms)
    );

  function isCustomDateField(field) {
    const element =
      getElement(field);

    return (
      getElementType(field) === "custom-date" &&
      element?.tagName === "BUTTON" &&
      element.getAttribute("aria-haspopup") === "dialog"
    );
  }

  function setNativeSelectValue(
    select,
    value
  ) {
    const descriptor =
      Object.getOwnPropertyDescriptor(
        HTMLSelectElement.prototype,
        "value"
      );

    if (descriptor?.set) {
      descriptor.set.call(
        select,
        String(value)
      );
    } else {
      select.value =
        String(value);
    }

    select.dispatchEvent(
      new Event(
        "input",
        { bubbles: true }
      )
    );

    select.dispatchEvent(
      new Event(
        "change",
        { bubbles: true }
      )
    );
  }

  function findOpenCalendar(trigger) {
    const controlledId =
      trigger?.getAttribute(
        "aria-controls"
      );

    const controlled =
      controlledId
        ? document.getElementById(
            controlledId
          )
        : null;

    const candidates = [
      controlled,
      ...document.querySelectorAll(
        '[role="dialog"], [data-radix-popper-content-wrapper], [data-state="open"]'
      )
    ].filter(Boolean);

    return (
      candidates.find(container => {
        if (
          !container.getClientRects().length
        ) {
          return false;
        }

        const selects =
          container.querySelectorAll(
            "select"
          );

        const dayButtons =
          Array.from(
            container.querySelectorAll(
              "button"
            )
          ).filter(button =>
            /^\\d{1,2}$/.test(
              String(
                button.textContent || ""
              ).trim()
            )
          );

        return (
          selects.length >= 2 ||
          dayButtons.length >= 20
        );
      }) ||
      null
    );
  }

  async function waitForOpenCalendar(
    trigger,
    timeout = 2500
  ) {
    const started =
      Date.now();

    while (
      Date.now() - started <
      timeout
    ) {
      const calendar =
        findOpenCalendar(
          trigger
        );

      if (calendar) {
        return calendar;
      }

      await careerSyncSleep(60);
    }

    return null;
  }

  function findCalendarSelects(calendar) {
    const selects =
      Array.from(
        calendar.querySelectorAll(
          "select"
        )
      );

    const month =
      selects.find(select => {
        const texts =
          Array.from(
            select.options
          ).map(option =>
            normalize(
              option.textContent
            )
          );

        return (
          texts.includes("january") &&
          texts.includes("december")
        );
      }) ||
      null;

    const year =
      selects.find(select =>
        Array.from(
          select.options
        ).some(option =>
          /^(19|20)\\d{2}$/.test(
            String(option.value)
          )
        )
      ) ||
      null;

    return {
      month,
      year
    };
  }

  async function fillCustomDatePicker(
    field,
    answer
  ) {
    const trigger =
      getElement(field);

    const parts =
      parseCareerSyncDate(
        answer
      );

    if (
      !trigger ||
      !isValidDateParts(parts)
    ) {
      return false;
    }

    trigger.click();

    let calendar =
      await waitForOpenCalendar(
        trigger
      );

    if (!calendar) {
      console.warn(
        `[CareerSync][DATE] Calendar did not open for "${getQuestion(field)}".`
      );

      return false;
    }

    let {
      month,
      year
    } =
      findCalendarSelects(
        calendar
      );

    // Select year first. React calendars commonly rerender here.
    if (year) {
      const yearOption =
        Array.from(
          year.options
        ).find(option =>
          String(option.value) ===
          String(parts.year)
        );

      if (!yearOption) {
        console.warn(
          `[CareerSync][DATE] Year ${parts.year} is not available in this calendar.`
        );

        return false;
      }

      setNativeSelectValue(
        year,
        parts.year
      );

      await careerSyncSleep(140);

      calendar =
        findOpenCalendar(
          trigger
        ) ||
        calendar;
    }

    ({
      month,
      year
    } =
      findCalendarSelects(
        calendar
      ));

    if (month) {
      const monthNames = [
        "january",
        "february",
        "march",
        "april",
        "may",
        "june",
        "july",
        "august",
        "september",
        "october",
        "november",
        "december"
      ];

      const options =
        Array.from(
          month.options
        );

      const named =
        options.find(option =>
          normalize(
            option.textContent
          ) ===
          monthNames[
            parts.month - 1
          ]
        );

      const zeroBased =
        options.find(option =>
          String(option.value) ===
          String(parts.month - 1)
        );

      const oneBased =
        options.find(option =>
          String(option.value) ===
          String(parts.month)
        );

      const selected =
        named ||
        (
          options.some(option =>
            String(option.value) === "0"
          )
            ? zeroBased
            : oneBased
        );

      if (!selected) {
        return false;
      }

      setNativeSelectValue(
        month,
        selected.value
      );

      await careerSyncSleep(160);

      calendar =
        findOpenCalendar(
          trigger
        ) ||
        calendar;
    }

    // Always re-query day after month/year changes because React rerenders.
    const dayButton =
      Array.from(
        calendar.querySelectorAll(
          "button"
        )
      ).find(button =>
        !button.disabled &&
        button.getClientRects().length &&
        String(
          button.textContent || ""
        ).trim() ===
          String(parts.day)
      );

    if (!dayButton) {
      return false;
    }

    dayButton.click();

    await careerSyncSleep(120);

    trigger.setAttribute(
      "data-careersync-filled",
      "true"
    );

    console.log(
      `[CareerSync][DATE] Selected ${pad2(parts.day)}/${pad2(parts.month)}/${parts.year} for "${getQuestion(field)}".`
    );

    return true;
  }


  // ============================================================
  // DATE NORMALIZATION
  //
  // Canonical profile DOB may be stored as DD/MM/YYYY or YYYY-MM-DD.
  // Native HTML date controls require YYYY-MM-DD. Text fields are
  // formatted according to their placeholder when possible.
  // ============================================================

  function parseCareerSyncDate(value) {
    const raw =
      String(value || "").trim();

    if (!raw) {
      return null;
    }

    let match;

    // YYYY-MM-DD / YYYY/MM/DD
    match = raw.match(
      /^(\d{4})[-\/](\d{1,2})[-\/](\d{1,2})$/
    );

    if (match) {
      return {
        year: Number(match[1]),
        month: Number(match[2]),
        day: Number(match[3])
      };
    }

    // DD/MM/YYYY or DD-MM-YYYY (CareerSync canonical human format)
    match = raw.match(
      /^(\d{1,2})[-\/](\d{1,2})[-\/](\d{4})$/
    );

    if (match) {
      return {
        day: Number(match[1]),
        month: Number(match[2]),
        year: Number(match[3])
      };
    }

    // ISO timestamp
    match = raw.match(
      /^(\d{4})-(\d{2})-(\d{2})T/
    );

    if (match) {
      return {
        year: Number(match[1]),
        month: Number(match[2]),
        day: Number(match[3])
      };
    }

    return null;
  }


  function isValidDateParts(parts) {
    if (!parts) {
      return false;
    }

    const {
      year,
      month,
      day
    } = parts;

    if (
      !year ||
      !month ||
      !day ||
      month < 1 ||
      month > 12 ||
      day < 1 ||
      day > 31
    ) {
      return false;
    }

    const date =
      new Date(
        year,
        month - 1,
        day
      );

    return (
      date.getFullYear() === year &&
      date.getMonth() === month - 1 &&
      date.getDate() === day
    );
  }


  function pad2(value) {
    return String(value)
      .padStart(2, "0");
  }


  function formatDateForField(
    field,
    value
  ) {
    const element =
      getElement(field);

    if (!element) {
      return String(
        value ?? ""
      ).trim();
    }

    const raw =
      String(
        value ?? ""
      ).trim();

    const parts =
      parseCareerSyncDate(raw);

    if (
      !isValidDateParts(parts)
    ) {
      return raw;
    }

    const yyyy =
      String(parts.year);

    const mm =
      pad2(parts.month);

    const dd =
      pad2(parts.day);

    const type =
      String(
        element.type || ""
      ).toLowerCase();

    // Native browser date input.
    if (type === "date") {
      return `${yyyy}-${mm}-${dd}`;
    }

    if (type === "month") {
      return `${yyyy}-${mm}`;
    }

    if (
      type === "datetime-local"
    ) {
      return `${yyyy}-${mm}-${dd}T00:00`;
    }

    const hint =
      String(
        element.placeholder ||
        element.getAttribute("aria-label") ||
        field?.placeholder ||
        ""
      ).toLowerCase();

    if (
      hint.includes("yyyy-mm-dd") ||
      hint.includes("yyyy/mm/dd")
    ) {
      return hint.includes("/")
        ? `${yyyy}/${mm}/${dd}`
        : `${yyyy}-${mm}-${dd}`;
    }

    if (
      hint.includes("mm/dd/yyyy") ||
      hint.includes("mm-dd-yyyy")
    ) {
      return hint.includes("-")
        ? `${mm}-${dd}-${yyyy}`
        : `${mm}/${dd}/${yyyy}`;
    }

    if (
      hint.includes("dd-mm-yyyy")
    ) {
      return `${dd}-${mm}-${yyyy}`;
    }

    // Default for normal text DOB fields.
    return `${dd}/${mm}/${yyyy}`;
  }


  function isCurrentDateField(field) {
    const context =
      normalize(
        getFieldContext(field)
      );

    // Only explicitly "today/current date" fields get today's date.
    // DOB and joining/start/end dates are NEVER replaced with today.
    return (
      /\b(current date|today s date|todays date|date today)\b/
        .test(context) &&
      !/\b(date of birth|birth date|dob|joining|start date|end date)\b/
        .test(context)
    );
  }


  function getTodayForField(field) {
    const now =
      new Date();

    const dd =
      pad2(now.getDate());

    const mm =
      pad2(now.getMonth() + 1);

    const yyyy =
      String(now.getFullYear());

    return formatDateForField(
      field,
      `${dd}/${mm}/${yyyy}`
    );
  }


  function fillAnswer(
    field,
    answer
  ) {
    const element =
      getElement(field);

    if (!element) {
      return false;
    }

    const type =
      getElementType(field);

    let value =
      String(
        answer ?? ""
      ).trim();

    if (
      isEmpty(value) &&
      isCurrentDateField(field)
    ) {
      value =
        getTodayForField(field);
    }

    if (
      !isEmpty(value) &&
      (
        type === "date" ||
        type === "month" ||
        type === "datetime-local" ||
        /\b(date of birth|birth date|dob|current date|today s date|todays date)\b/
          .test(
            normalize(
              getFieldContext(field)
            )
          )
      )
    ) {
      value =
        formatDateForField(
          field,
          value
        );
    }

    if (
      isEmpty(value) &&
      type !== "checkbox"
    ) {
      return false;
    }

    // SELECT
    if (
      type === "select"
    ) {
      return fillSelect(
        element,
        value
      );
    }

    // CHECKBOX
    if (
      type === "checkbox"
    ) {
      const shouldCheck =
        /^(yes|true|1|agree|agreed|checked)$/i
          .test(value);

      if (
        element.checked !==
        shouldCheck
      ) {
        element.click();
      }

      element.dispatchEvent(
        new Event(
          "input",
          {
            bubbles: true
          }
        )
      );

      element.dispatchEvent(
        new Event(
          "change",
          {
            bubbles: true
          }
        )
      );

      element.setAttribute(
        "data-careersync-filled",
        "true"
      );

      return (
        element.checked ===
        shouldCheck
      );
    }

    // RADIO
    if (
      type === "radio"
    ) {
      if (
        !element.name
      ) {
        const label =
          getRadioLabel(element);

        if (
          normalize(element.value) ===
            normalize(value) ||
          normalize(label) ===
            normalize(value)
        ) {
          element.click();

          return true;
        }

        return false;
      }

      const radios =
        getRadioGroupElements(element);

      const target =
        radios.find(radio => {
          const label =
            getRadioLabel(radio);

          return (
            normalize(radio.value) ===
              normalize(value) ||
            normalize(label) ===
              normalize(value) ||
            normalize(label).includes(
              normalize(value)
            ) ||
            normalize(value).includes(
              normalize(label)
            )
          );
        });

      if (!target) {
        return false;
      }

      target.click();

      target.dispatchEvent(
        new Event(
          "input",
          {
            bubbles: true
          }
        )
      );

      target.dispatchEvent(
        new Event(
          "change",
          {
            bubbles: true
          }
        )
      );

      target.setAttribute(
        "data-careersync-filled",
        "true"
      );

      return true;
    }

    // TEXT / EMAIL / TEL / URL / NUMBER / DATE / TEXTAREA
    try {
      const success =
        filler.fill(
          element,
          value
        );

      if (success) {
        return true;
      }
    }
    catch (error) {
      console.warn(
        "[CareerSync] FieldFiller failed, using native fallback:",
        error
      );
    }

    // Native fallback
    try {
      const prototype =
        Object.getPrototypeOf(
          element
        );

      const descriptor =
        Object.getOwnPropertyDescriptor(
          prototype,
          "value"
        );

      if (
        descriptor?.set
      ) {
        descriptor.set.call(
          element,
          value
        );
      }
      else {
        element.value =
          value;
      }

      element.dispatchEvent(
        new Event(
          "input",
          {
            bubbles: true
          }
        )
      );

      element.dispatchEvent(
        new Event(
          "change",
          {
            bubbles: true
          }
        )
      );

      element.dispatchEvent(
        new Event(
          "blur",
          {
            bubbles: true
          }
        )
      );

      element.setAttribute(
        "data-careersync-filled",
        "true"
      );

      return (
        String(
          element.value ?? ""
        ).trim() === value
      );
    }
    catch (error) {
      console.error(
        "[CareerSync] Could not fill field:",
        getQuestion(field),
        error
      );

      return false;
    }
  }

  // ============================================================
  // ASK USER
  // ============================================================

  function shouldAskUser(field) {
    return (
      isAnswerableField(field) &&
      !currentFieldHasValue(field)
    );
  }

  async function askUserForField(
    field,
    index,
    total,
    profileMatch = null
  ) {
    const question =
      getQuestion(field);

    let choices =
      getFieldChoices(field);

    if (getElementType(field) === "custom-select" && !choices.length) {
      choices = await getCustomSelectChoices(field);
    }

    getElement(field)
      ?.scrollIntoView({
        behavior:
          "smooth",

        block:
          "center"
      });

    return new Promise(
      resolve => {

        confidenceUI.showPrompt({
          field,

          question,

          choices,

          index,

          total,

          onSave:
            async answer => {
              try {
                // If matchField recognized this as a canonical
                // CareerSync profile field, persist it in the
                // per-user Extension Profile.
                if (profileMatch?.key) {
                  await updateExtensionProfile(
                    profileMatch.key,
                    answer
                  );

                  console.log(
                    `[CareerSync] Saved "${question}" to extension profile.${profileMatch.key}`
                  );
                }
                else {
                  // Truly application-specific / unknown question:
                  // keep using learned Neon memory.
                  await saveMemory({
                    question,
                    answer,
                    field
                  });

                  console.log(
                    `[CareerSync] Saved application-specific "${question}" to learned memory.`
                  );
                }

                const success =
                  getElementType(field) === "custom-select"
                    ? await fillCustomSelect(field, answer)
                    : fillAnswer(field, answer);

                console.log(
                  `[CareerSync] Learned "${question}" = "${answer}" | Filled=${success}`
                );

                resolve(success);

                return true;
              }
              catch (error) {
                console.error(
                  `[CareerSync] Could not save "${question}":`,
                  error
                );

                throw error;
              }
            },

          onSkip:
            () => {
              console.log(
                `[CareerSync] Skipped "${question}"`
              );

              resolve(false);
            }
        });
      }
    );
  }


  // ============================================================
  // DEDUPLICATE RADIO GROUPS / REPEATED SCANNER RESULTS
  // ============================================================

  function deduplicateFields(
    items
  ) {
    const result = [];
    const seen = new Set();

    for (
      const item of items
    ) {
      const field =
        item?.field || item;

      const element =
        getElement(field);

      const type =
        getElementType(field);

      const key =
        type === "radio" &&
        element?.name

          ? `radio:${element.name}`

          : [
              normalize(
                getQuestion(field)
              ),
              type,
              element?.name || "",
              element?.id || ""
            ].join(":");

      if (
        seen.has(key)
      ) {
        continue;
      }

      seen.add(key);

      result.push(
        item?.field
          ? item
          : {
              field,
              profileMatch: null
            }
      );
    }

    return result;
  }


  // ============================================================
  // MAIN AUTOFILL
  // ============================================================

  async function runAutofill() {
    if (
      autofillRunning
    ) {
      console.log("[CareerSync] Duplicate Autofill click ignored because a run is already active.");
      return {
        success: true,
        alreadyRunning: true,
        message: "CareerSync autofill is already running."
      };
    }

    autofillRunning =
      true;

    try {
      console.log(
        "[CareerSync] Starting form scan..."
      );

      // Fresh data on each explicit Autofill click.
      // This prevents stale cached profile / memory values.
      const [
        profile,
        memories
      ] =
        await Promise.all([
          getProfile(true),
          getMemory(true)
        ]);

      const values =
        buildProfileValues(
          profile
        );

      const fields =
        scanFields();

      let matched = 0;
      let filled = 0;
      let missingProfile = 0;
      let memoryFilled = 0;
      let learned = 0;

      const unknownFields =
        [];

      // ------------------------------------------------------
      // PASS 1
      //
      // IMPORTANT:
      // We DO NOT skip a field just because Chrome/browser has
      // placed some value in it. CareerSync profile/memory gets
      // first priority and may overwrite browser autofill.
      // ------------------------------------------------------

      for (
        const field of fields
      ) {
        if (
          !isAnswerableField(
            field
          )
        ) {
          continue;
        }

        const question =
          getQuestion(field);

        const context =
          getFieldContext(field);

        console.log(
          "[CareerSync] Processing field:",
          {
            question,
            type:
              getElementType(field),
            context,
            currentValue:
              getElement(field)?.value
          }
        );

        // Absolute safety boundary: never answer user legal decisions or passwords.
        if (isUserDecisionOnlyField(field) || getElementType(field)==="password") {
          console.log(`[CareerSync][HARD SKIP] User-only/password field untouched: "${question}".`);
          continue;
        }

        if (isCustomSelectField(field)) {
          const profileMatch=matchField(field,values);
          const exact=findExactMemoryMatch(field,memories);
          const fuzzy=findMemoryMatch(field,memories,profileMatch);
          const direct=!isEmpty(profileMatch?.value)?profileMatch.value:(!isEmpty(exact?.answer)?exact.answer:(!isEmpty(fuzzy?.answer)?fuzzy.answer:""));
          if(!isEmpty(direct) && await fillCustomSelect(field,direct)) { matched++; filled++; continue; }
          unknownFields.push({field,profileMatch});
          console.log(`[CareerSync][CUSTOM SELECT QUEUED] "${question}".`);
          continue;
        }

        // ==================================================
        // CUSTOM DATE FIELD
        // Profile factual date -> calendar selection.
        // Explicit "current/today date" -> today's date.
        // Missing factual date remains unresolved and follows normal
        // CareerSync ask/learn flow; legal decisions never reach here.
        // ==================================================
        if (
          isCustomDateField(field)
        ) {
          const profileMatch =
            matchField(
              field,
              values
            );

          let dateAnswer =
            profileMatch &&
            !isEmpty(
              profileMatch.value
            )
              ? profileMatch.value
              : "";

          if (
            isEmpty(dateAnswer) &&
            isCurrentDateField(field)
          ) {
            dateAnswer =
              getTodayForField(
                field
              );
          }

          if (
            !isEmpty(dateAnswer)
          ) {
            const success =
              await fillCustomDatePicker(
                field,
                dateAnswer
              );

            if (success) {
              matched +=
                profileMatch
                  ? 1
                  : 0;

              filled++;

              console.log(
                `[CareerSync][CUSTOM DATE] AUTO-FILLED "${question}".`
              );

              continue;
            }
          }

          unknownFields.push({
            field,
            profileMatch
          });

          console.log(
            `[CareerSync][CUSTOM DATE] "${question}" needs a factual date answer.`
          );

          continue;
        }

        // ==================================================
        // LAYER 1 - SAVED CUSTOM / LEARNED ANSWER (OFFLINE)
        // Same question seen before? Use it immediately.
        // No Groq / AI request is made.
        // ==================================================
        const exactMemoryMatch =
          findExactMemoryMatch(
            field,
            memories
          );

        if (
          exactMemoryMatch &&
          !isEmpty(exactMemoryMatch.answer)
        ) {
          const success =
            fillAnswer(
              field,
              exactMemoryMatch.answer
            );

          if (success) {
            filled++;
            memoryFilled++;

            console.log(
              `[CareerSync][L1 OFFLINE MEMORY] AUTO-FILLED "${question}" (${exactMemoryMatch.reason}).`
            );

            continue;
          }

          console.log(
            `[CareerSync][L1 OFFLINE MEMORY] Answer exists for "${question}" but does not directly fit this field/choice. It will be adapted only if later layers can resolve it.`
          );
        }

        // ==================================================
        // LAYER 2 - OFFLINE PROFILE PATTERN MATCHING
        // Regex/aliases/HTML metadata map the question to a
        // canonical Extension Profile field. Still NO AI.
        // Example: Provide your name -> fullName, Major -> branch.
        // ==================================================
        const profileMatch =
          matchField(
            field,
            values
          );

        if (profileMatch) {
          matched++;

          if (!isEmpty(profileMatch.value)) {
            const success =
              fillAnswer(
                field,
                profileMatch.value
              );

            if (success) {
              filled++;

              console.log(
                `[CareerSync][L2 OFFLINE PATTERN] AUTO-FILLED "${question}" from profile.${profileMatch.key}`
              );

              continue;
            }

            console.log(
              `[CareerSync][L2 OFFLINE PATTERN] profile.${profileMatch.key} matched "${question}", but its value does not directly fit the form choices. AI may adapt only this unresolved field.`,
              profileMatch
            );
          } else {
            missingProfile++;

            console.log(
              `[CareerSync][L2 OFFLINE PATTERN] Recognized profile.${profileMatch.key}, but saved value is empty for "${question}".`
            );
          }
        }

        // ==================================================
        // LAYER 2B - OFFLINE FUZZY/CANONICAL MEMORY
        // Small wording variations are reused without AI.
        // ==================================================
        const memoryMatch =
          findMemoryMatch(
            field,
            memories,
            profileMatch
          );

        if (
          memoryMatch &&
          !isEmpty(memoryMatch.answer)
        ) {
          const success =
            fillAnswer(
              field,
              memoryMatch.answer
            );

          if (success) {
            filled++;
            memoryFilled++;

            console.log(
              `[CareerSync][L2B OFFLINE MEMORY] AUTO-FILLED "${question}" (${memoryMatch.reason || "match"}).`
            );

            continue;
          }

          console.log(
            `[CareerSync][L2B OFFLINE MEMORY] Candidate found for "${question}" but it cannot be inserted directly. AI may adapt this unresolved field.`
          );
        }

        // ==================================================
        // LAYER 3 CANDIDATE
        // Only fields that survived ALL offline layers are queued
        // for semantic AI matching. Direct/profile matches NEVER
        // go to Groq.
        // ==================================================
        unknownFields.push({
          field,
          profileMatch
        });

        console.log(
          `[CareerSync][L3 QUEUED] "${question}" | type=${getElementType(field)} | offline layers unresolved`
        );
      }

      // ------------------------------------------------------
      // DYNAMIC MULTI-PASS RESCAN
      // ATS forms frequently reveal dependent fields only after a parent
      // answer is selected (UG -> Degree/College/Branch, CGPA -> value,
      // Country -> State -> City, Yes -> follow-up questions).  Before AI or
      // user prompts, wait for the framework to render and restart the full
      // deterministic pipeline when genuinely new logical fields appeared.
      // ------------------------------------------------------
      await careerSyncSleep(500);
      const rescannedFields = scanFields();
      const beforeKeys = new Set(fields.map(getDetectedFieldKey));
      const newlyRendered = rescannedFields.filter(f => !beforeKeys.has(getDetectedFieldKey(f)));

      if (newlyRendered.length && dynamicRestartDepth < 5) {
        dynamicRestartDepth += 1;
        console.log(
          `[CareerSync][DYNAMIC PASS ${dynamicRestartDepth}] ${newlyRendered.length} new field(s) rendered. Re-scanning BEFORE AI/user prompts:`,
          newlyRendered.map(getQuestion)
        );
        autofillRunning = false;
        return await runAutofill();
      }

      if (!newlyRendered.length || dynamicRestartDepth >= 5) {
        if (dynamicRestartDepth >= 5 && newlyRendered.length) {
          console.warn('[CareerSync][DYNAMIC PASS] Maximum 5 dependency passes reached; continuing safely.');
        }
        dynamicRestartDepth = 0;
      }

      const uniqueUnknown =
        deduplicateFields(unknownFields).filter(item =>
          isAnswerableField(item.field) &&
          !isUserDecisionOnlyField(item.field) &&
          getElementType(item.field) !== "password"
        );

      // Custom date pickers need a real date value, not an AI guess.
      // Ask only when the canonical factual date is missing.
      const customDateUnknown =
        uniqueUnknown.filter(
          item =>
            isCustomDateField(
              item.field
            )
        );

      const aiEligibleUnknown =
        uniqueUnknown.filter(
          item =>
            !isCustomDateField(
              item.field
            ) &&
            !isUserDecisionOnlyField(
              item.field
            )
        );

      console.log(
        `[CareerSync] Unknown unanswered fields: ${uniqueUnknown.length}`,
        uniqueUnknown.map(
          item => getQuestion(item.field)
        )
      );

      // ------------------------------------------------------
      // LAYER 3 - AI SEMANTIC MATCHING (ONLY UNRESOLVED)
      //
      // This is intentionally the LAST matching layer, mirroring the
      // reference architecture: Custom Q&A -> Offline Pattern -> AI.
      // Groq receives ONLY fields that could not be filled by exact memory,
      // canonical profile patterns, or offline fuzzy memory.
      // ------------------------------------------------------

      let aiFilled = 0;
      const stillUnknown = [];

      if (
        aiEligibleUnknown.length
      ) {
        try {
          console.log(
            `[CareerSync][L3 AI] Offline layers could not resolve ${aiEligibleUnknown.length} field(s). Sending ONLY those fields for semantic matching...`
          );

          const aiResults =
            await getAISuggestions(
              aiEligibleUnknown
            );

          const aiByIndex =
            new Map(
              aiResults.map(
                result => [
                  Number(result.index),
                  result
                ]
              )
            );

          for (
            let i = 0;
            i < aiEligibleUnknown.length;
            i++
          ) {
            const item =
              aiEligibleUnknown[i];

            const field =
              item.field;

            const suggestion =
              aiByIndex.get(i);

            const confidence =
              Number(
                suggestion?.confidence || 0
              );

            console.log(
              `[CareerSync][L3 AI RESULT] "${getQuestion(field)}" | canAnswer=${Boolean(suggestion?.canAnswer)} | answer=${JSON.stringify(suggestion?.answer ?? null)} | confidence=${Math.round(confidence * 100)}% | reason=${suggestion?.reason || "none"}`
            );

            if (
              suggestion?.canAnswer &&
              !isEmpty(
                suggestion.answer
              ) &&
              confidence >= 0.80
            ) {
              const compatibleAnswer =
                coerceAnswerToAllowedChoice(
                  field,
                  suggestion.answer
                );

              if (compatibleAnswer === null) {
                console.warn(
                  `[CareerSync][L3 AI] Rejected incompatible answer "${suggestion.answer}" for "${getQuestion(field)}" because it is not one of the field's allowed choices.`
                );

                stillUnknown.push(item);
                continue;
              }

              const success =
                isCustomSelectField(field)
                  ? await fillCustomSelect(field, compatibleAnswer)
                  : fillAnswer(field, compatibleAnswer);

              if (
                success
              ) {
                filled++;
                aiFilled++;

                console.log(
                  `[CareerSync][L3 AI] AI-FILLED "${getQuestion(field)}" = "${compatibleAnswer}" (${Math.round(confidence * 100)}%) | ${suggestion.reason || "semantic-profile-match"}`
                );

                // Persist the resolved wording as learned memory.
                // We intentionally do NOT overwrite canonical profile
                // data with transformed values such as Female -> She/her.
                try {
                  await saveMemory({
                    question:
                      getQuestion(field),

                    answer:
                      compatibleAnswer,

                    field,

                    source:
                      "ai",

                    confidence
                  });
                }
                catch (memoryError) {
                  console.warn(
                    `[CareerSync] AI filled field but could not save memory for "${getQuestion(field)}":`,
                    memoryError
                  );
                }

                continue;
              }

              console.warn(
                `[CareerSync] AI suggested "${suggestion.answer}" for "${getQuestion(field)}" but the field could not accept it.`
              );
            }

            stillUnknown.push(
              item
            );
          }
        }
        catch (aiError) {
          console.warn(
            "[CareerSync] AI fallback unavailable; continuing with user prompts:",
            aiError
          );

          stillUnknown.push(
            ...aiEligibleUnknown
          );
        }
      }

      // ------------------------------------------------------
      // PASS 3 - ASK USER ONLY FOR WHAT PROFILE + MEMORY + AI
      // COULD NOT SAFELY RESOLVE.
      // ------------------------------------------------------

      console.log(
        `[CareerSync] AI processing complete. Auto-filled by AI=${aiFilled}; explicit user answers still needed=${stillUnknown.length}.`
      );

      // Ask missing custom factual dates without sending them to AI.
      for (
        let i = 0;
        i < customDateUnknown.length;
        i++
      ) {
        const item =
          customDateUnknown[i];

        const field =
          item.field;

        const profileMatch =
          item.profileMatch;

        if (
          isUserDecisionOnlyField(
            field
          )
        ) {
          continue;
        }

        const choices =
          [];

        const answer =
          await confidenceUI.showPrompt({
            question:
              getQuestion(field),
            choices,
            index:
              i + 1,
            total:
              customDateUnknown.length
          });

        if (
          answer === null ||
          answer === undefined ||
          isEmpty(answer)
        ) {
          continue;
        }

        const success =
          await fillCustomDatePicker(
            field,
            answer
          );

        if (!success) {
          console.warn(
            `[CareerSync][DATE] Could not select user-entered date for "${getQuestion(field)}".`
          );

          continue;
        }

        if (
          profileMatch?.key
        ) {
          await updateExtensionProfile(
            profileMatch.key,
            answer
          );
        } else {
          await saveMemory({
            question:
              getQuestion(field),
            answer,
            field,
            source: "manual",
            confidence: 1
          });
        }

        filled++;
        learned++;
      }


      for (
        let i = 0;
        i < stillUnknown.length;
        i++
      ) {
        const item =
          stillUnknown[i];

        const field =
          item.field;

        const profileMatch =
          item.profileMatch;

        const success =
          await askUserForField(
            field,
            i + 1,
            stillUnknown.length,
            profileMatch
          );

        if (
          success
        ) {
          filled++;
          learned++;
        }
      }

      console.log(
        `[CareerSync] Done. Detected=${fields.length}, Matched=${matched}, Filled=${filled}, MissingProfile=${missingProfile}, MemoryFilled=${memoryFilled}, AIFilled=${aiFilled}, Learned=${learned}, Asked=${stillUnknown.length}`
      );

      return {
        success: true,

        detected:
          fields.length,

        matched,

        filled,

        missing:
          missingProfile,

        memoryFilled,

        aiFilled,

        learned,

        asked:
          stillUnknown.length
      };
    }
    catch (error) {
      console.error(
        "[CareerSync] Autofill failed:",
        error
      );

      return {
        success: false,
        error:
          error.message
      };
    }
    finally {
      autofillRunning =
        false;
    }
  }

  // ============================================================
  // POPUP MESSAGES
  // ============================================================

  chrome.runtime.onMessage.addListener(
    (
      message,
      sender,
      sendResponse
    ) => {
      if (
        message?.type ===
        "CAREERSYNC_AUTOFILL"
      ) {
        runAutofill()
          .then(
            sendResponse
          )
          .catch(
            error => {
              sendResponse({
                success:
                  false,

                error:
                  error.message
              });
            }
          );

        return true;
      }

      if (
        message?.type ===
        "CAREERSYNC_SCAN"
      ) {
        const fields =
          scanFields();

        sendResponse({
          success: true,
          detected:
            fields.length
        });
      }
    }
  );

  // ============================================================
  // DYNAMIC FORMS
  // ============================================================

  const observer =
    new DOMObserver(
      () => {
        console.log(
          "[CareerSync] Dynamic form change detected."
        );
      }
    );

  observer.start();

  // ============================================================
  // DEV HELPERS
  // ============================================================

  window.CareerSyncAutofill = {
    scan:
      () => scanFields(),

    run:
      runAutofill,

    profile:
      () => getProfile(true),

    memory:
      () => getMemory(true),

    clearCache:
      () => {
        cachedProfile = null;
        cachedMemory = null;

        console.log(
          "[CareerSync] Cache cleared."
        );
      }
  };
})();
