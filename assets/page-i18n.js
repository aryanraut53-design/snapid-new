(function () {
  const LANG_KEY = "snapid-lang";
  const supported = ["en", "ne", "hi"];

  const common = {
    en: {
      langShort: "EN",
      switchLanguage: "Switch language",
      backHome: "Back Home",
      guideNav: "Guide",
      historyNav: "History",
      faqNav: "FAQ",
      openHistory: "Open History",
      aboutTitle: "About | SnapID.Pro",
      faqTitle: "FAQ | SnapID.Pro",
      guideTitle: "How to Use | SnapID.Pro",
      historyTitle: "History | SnapID.Pro",
    },
    ne: {
      langShort: "ने",
      switchLanguage: "भाषा बदल्नुहोस्",
      backHome: "घर फर्कनुहोस्",
      guideNav: "मार्गदर्शिका",
      historyNav: "इतिहास",
      faqNav: "FAQ",
      openHistory: "इतिहास खोल्नुहोस्",
      aboutTitle: "हाम्रो बारेमा | SnapID.Pro",
      faqTitle: "FAQ | SnapID.Pro",
      guideTitle: "कसरी प्रयोग गर्ने | SnapID.Pro",
      historyTitle: "इतिहास | SnapID.Pro",
    },
    hi: {
      langShort: "हि",
      switchLanguage: "भाषा बदलें",
      backHome: "घर वापस",
      guideNav: "गाइड",
      historyNav: "इतिहास",
      faqNav: "FAQ",
      openHistory: "इतिहास खोलें",
      aboutTitle: "परिचय | SnapID.Pro",
      faqTitle: "FAQ | SnapID.Pro",
      guideTitle: "कैसे इस्तेमाल करें | SnapID.Pro",
      historyTitle: "इतिहास | SnapID.Pro",
    },
  };

  const pages = {
    about: {
      en: {
        pageTitle: "About | SnapID.Pro",
        aboutEyebrow: "About SnapID.Pro",
        aboutHeading: "Built to make passport photos simple, trustworthy, and print-ready.",
        aboutIntro: "SnapID.Pro helps students, families, and professionals generate clean passport photo sheets in minutes. Our workflow combines guided cropping, AI-assisted background cleanup, smart enhancement, and A4 PDF output tuned for real-world print shops.",
        reliabilityTitle: "Reliability First",
        reliabilityBody: "The app is engineered with graceful fallbacks so temporary AI-service issues do not block final PDF generation.",
        privacyTitle: "Privacy Aware",
        privacyBody: "Security headers, token-gated access, CSRF protection, and session checks are built in to reduce misuse risks.",
        printTitle: "Print Accuracy",
        printBody: "Output is laid out on A4 at 300 DPI with configurable dimensions, spacing, and border so final sheets are press-ready.",
        worksTitle: "How SnapID.Pro Works",
        step1Title: "1. Upload & Crop",
        step1Body: "Upload one or many photos and crop with passport ratio guidance.",
        step2Title: "2. AI Refinement",
        step2Body: "Background removal and enhancement are applied with automatic mode selection.",
        step3Title: "3. Quality Checks",
        step3Body: "Validation and safe defaults keep dimensions, spacing, and copies within sensible limits.",
        step4Title: "4. Export PDF",
        step4Body: "Get a downloadable multi-page PDF tailored for straightforward photo printing.",
        trustTitle: "Trust & Transparency",
        trustItem1: "Clear status feedback for success, partial AI processing, and recoverable failures.",
        trustItem2: "Rate limiting to protect availability and prevent abuse.",
        trustItem3: "Defensive backend error handling to avoid vague, silent failures.",
        helpTitle: "Need Help?",
        helpBody: "We welcome feedback and bug reports to keep improving accuracy and usability.",
      },
      ne: {
        pageTitle: "हाम्रो बारेमा | SnapID.Pro",
        aboutEyebrow: "SnapID.Pro बारेमा",
        aboutHeading: "पासपोर्ट फोटो सरल, भरोसायोग्य र प्रिन्ट-रेडी बनाउन बनाइएको।",
        aboutIntro: "SnapID.Pro ले विद्यार्थी, परिवार र पेशेवरलाई केही मिनेटमै सफा पासपोर्ट फोटो शीट बनाउन मद्दत गर्छ। यसमा गाइडेड क्रपिङ, AI ब्याकग्राउन्ड सफाइ, स्मार्ट सुधार र A4 PDF आउटपुट छ।",
        reliabilityTitle: "पहिले विश्वसनीयता",
        reliabilityBody: "अस्थायी AI सेवा समस्याले अन्तिम PDF रोक्न नपाओस् भनेर fallback सहित बनाइएको छ।",
        privacyTitle: "गोपनीयता सचेत",
        privacyBody: "Security headers, token access, CSRF protection र session checks misuse घटाउन जोडिएका छन्।",
        printTitle: "प्रिन्ट शुद्धता",
        printBody: "A4 मा 300 DPI सहित dimension, spacing र border मिलाएर print-ready sheet बनाइन्छ।",
        worksTitle: "SnapID.Pro कसरी काम गर्छ",
        step1Title: "1. अपलोड र क्रप",
        step1Body: "एक वा धेरै फोटो अपलोड गरेर passport ratio अनुसार crop गर्नुहोस्।",
        step2Title: "2. AI सुधार",
        step2Body: "Automatic mode selection सहित background removal र enhancement लागू हुन्छ।",
        step3Title: "3. गुणस्तर जाँच",
        step3Body: "Dimension, spacing र copies लाई सुरक्षित सीमाभित्र राखिन्छ।",
        step4Title: "4. PDF export",
        step4Body: "Photo printing का लागि मिलेको downloadable multi-page PDF पाउनुहोस्।",
        trustTitle: "विश्वास र पारदर्शिता",
        trustItem1: "Success, partial AI processing र recoverable failures का लागि clear status feedback।",
        trustItem2: "Availability बचाउन र abuse रोक्न rate limiting।",
        trustItem3: "Silent failures घटाउन defensive backend error handling।",
        helpTitle: "सहयोग चाहियो?",
        helpBody: "Accuracy र usability सुधार्न feedback र bug reports स्वागत छ।",
      },
      hi: {
        pageTitle: "परिचय | SnapID.Pro",
        aboutEyebrow: "SnapID.Pro के बारे में",
        aboutHeading: "पासपोर्ट फोटो को आसान, भरोसेमंद और print-ready बनाने के लिए बनाया गया।",
        aboutIntro: "SnapID.Pro students, families और professionals को कुछ मिनटों में साफ passport photo sheets बनाने में मदद करता है। इसमें guided cropping, AI background cleanup, smart enhancement और A4 PDF output शामिल है।",
        reliabilityTitle: "Reliability First",
        reliabilityBody: "App में graceful fallbacks हैं ताकि temporary AI-service issue final PDF generation को block न करे।",
        privacyTitle: "Privacy Aware",
        privacyBody: "Security headers, token-gated access, CSRF protection और session checks misuse risk कम करते हैं।",
        printTitle: "Print Accuracy",
        printBody: "Output A4 पर 300 DPI में configurable dimensions, spacing और border के साथ तैयार होता है।",
        worksTitle: "SnapID.Pro कैसे काम करता है",
        step1Title: "1. Upload और Crop",
        step1Body: "एक या कई photos upload करें और passport ratio guidance से crop करें।",
        step2Title: "2. AI Refinement",
        step2Body: "Background removal और enhancement automatic mode selection के साथ apply होते हैं।",
        step3Title: "3. Quality Checks",
        step3Body: "Validation और safe defaults dimensions, spacing और copies को sensible limits में रखते हैं।",
        step4Title: "4. PDF Export",
        step4Body: "Photo printing के लिए तैयार downloadable multi-page PDF पाएं।",
        trustTitle: "Trust और Transparency",
        trustItem1: "Success, partial AI processing और recoverable failures के लिए clear status feedback।",
        trustItem2: "Availability protect करने और abuse रोकने के लिए rate limiting।",
        trustItem3: "Vague silent failures से बचने के लिए defensive backend error handling।",
        helpTitle: "Help चाहिए?",
        helpBody: "Accuracy और usability सुधारने के लिए feedback और bug reports welcome हैं।",
      },
    },
    faq: {
      en: {
        pageTitle: "FAQ | SnapID.Pro",
        faqHeading: "Frequently Asked Questions",
        faqIntro: "Everything users usually ask before printing passport photos.",
        q1: "Is my output print-ready?",
        a1: "Yes. PDFs are generated on A4 at high resolution with configurable spacing and border for common print shops.",
        q2: "What if background removal fails?",
        a2: "The app now fails softly and continues with the original image, so you still get a PDF instead of a hard error.",
        q3: "How many files can I store in history?",
        a3: "There is no app-imposed limit. History is stored in IndexedDB and grows until your browser storage quota is reached.",
        q4: "Can I download old PDFs later?",
        a4: "Yes. Go to the History page to preview, download, or remove any previously generated file.",
      },
      ne: {
        pageTitle: "FAQ | SnapID.Pro",
        faqHeading: "धेरै सोधिने प्रश्नहरू",
        faqIntro: "Passport photo print गर्नु अघि users ले प्रायः सोध्ने कुरा।",
        q1: "मेरो output print-ready हुन्छ?",
        a1: "हुन्छ। PDF हरू A4 मा high resolution, configurable spacing र border सहित बनाइन्छ।",
        q2: "Background removal fail भयो भने?",
        a2: "App ले original image बाट पनि PDF बनाउन जारी राख्छ, त्यसैले hard error आउँदैन।",
        q3: "History मा कति files store गर्न सक्छु?",
        a3: "App ले limit लगाउँदैन। History IndexedDB मा browser storage quota पुग्दासम्म बस्छ।",
        q4: "पुराना PDFs पछि download गर्न मिल्छ?",
        a4: "मिल्छ। History page मा गएर preview, download वा remove गर्न सक्नुहुन्छ।",
      },
      hi: {
        pageTitle: "FAQ | SnapID.Pro",
        faqHeading: "अक्सर पूछे जाने वाले सवाल",
        faqIntro: "Passport photos print करने से पहले users आम तौर पर यही पूछते हैं।",
        q1: "क्या मेरा output print-ready होगा?",
        a1: "हाँ। PDFs A4 पर high resolution में configurable spacing और border के साथ बनते हैं।",
        q2: "Background removal fail हो जाए तो?",
        a2: "App original image के साथ PDF बनाना continue करता है, इसलिए hard error नहीं आता।",
        q3: "History में कितनी files store कर सकता हूं?",
        a3: "App कोई limit नहीं लगाता। History IndexedDB में browser storage quota तक रहती है।",
        q4: "क्या पुराने PDFs बाद में download कर सकता हूं?",
        a4: "हाँ। History page पर जाकर preview, download या remove कर सकते हैं।",
      },
    },
    guide: {
      en: {
        pageTitle: "How to Use | SnapID.Pro",
        guideHeading: "How to Use SnapID.Pro",
        guideIntro: "A practical guide to get a clean result on the first try.",
        stepLabel1: "Step 1",
        guideStep1Title: "Upload a clear photo",
        guideStep1Body: "Use a front-facing image with proper lighting and simple background for best AI cleanup.",
        stepLabel2: "Step 2",
        guideStep2Title: "Crop precisely",
        guideStep2Body: "Use the crop tool to center the face and keep chin-to-head ratio passport-friendly.",
        stepLabel3: "Step 3",
        guideStep3Title: "Pick enhancement mode",
        guideStep3Body: "Auto Detect works for most users. Use Brighten for dark photos and Fix Color for warm/yellow casts.",
        stepLabel4: "Step 4",
        guideStep4Title: "Generate and preview PDF",
        guideStep4Body: "Click Generate Print Sheet. Review the preview and then download.",
        stepLabel5: "Step 5",
        guideStep5Title: "Use History for later",
        guideStep5Body: "Every generated PDF is auto-saved in your browser history (IndexedDB), with download/view/delete support.",
      },
      ne: {
        pageTitle: "कसरी प्रयोग गर्ने | SnapID.Pro",
        guideHeading: "SnapID.Pro कसरी प्रयोग गर्ने",
        guideIntro: "पहिलो प्रयासमै सफा result पाउन practical guide।",
        stepLabel1: "चरण 1",
        guideStep1Title: "सफा photo upload गर्नुहोस्",
        guideStep1Body: "Best AI cleanup का लागि front-facing, राम्रो lighting र simple background भएको image प्रयोग गर्नुहोस्।",
        stepLabel2: "चरण 2",
        guideStep2Title: "ठ्याक्कै crop गर्नुहोस्",
        guideStep2Body: "Face center मा राख्न र chin-to-head ratio passport-friendly बनाउन crop tool प्रयोग गर्नुहोस्।",
        stepLabel3: "चरण 3",
        guideStep3Title: "Enhancement mode छान्नुहोस्",
        guideStep3Body: "धेरै users का लागि Auto Detect ठीक हुन्छ। Dark photo का लागि Brighten र yellow cast का लागि Fix Color प्रयोग गर्नुहोस्।",
        stepLabel4: "चरण 4",
        guideStep4Title: "PDF generate र preview गर्नुहोस्",
        guideStep4Body: "Generate Print Sheet click गर्नुहोस्। Preview हेरेर download गर्नुहोस्।",
        stepLabel5: "चरण 5",
        guideStep5Title: "पछि History प्रयोग गर्नुहोस्",
        guideStep5Body: "हरेक generated PDF browser history (IndexedDB) मा auto-save हुन्छ, download/view/delete support सहित।",
      },
      hi: {
        pageTitle: "कैसे इस्तेमाल करें | SnapID.Pro",
        guideHeading: "SnapID.Pro कैसे इस्तेमाल करें",
        guideIntro: "पहली कोशिश में clean result पाने के लिए practical guide।",
        stepLabel1: "Step 1",
        guideStep1Title: "Clear photo upload करें",
        guideStep1Body: "Best AI cleanup के लिए front-facing image, proper lighting और simple background use करें।",
        stepLabel2: "Step 2",
        guideStep2Title: "Precisely crop करें",
        guideStep2Body: "Face center में रखने और chin-to-head ratio passport-friendly रखने के लिए crop tool use करें।",
        stepLabel3: "Step 3",
        guideStep3Title: "Enhancement mode चुनें",
        guideStep3Body: "Most users के लिए Auto Detect ठीक है। Dark photos के लिए Brighten और yellow casts के लिए Fix Color use करें।",
        stepLabel4: "Step 4",
        guideStep4Title: "PDF generate और preview करें",
        guideStep4Body: "Generate Print Sheet click करें। Preview review करें और फिर download करें।",
        stepLabel5: "Step 5",
        guideStep5Title: "बाद में History use करें",
        guideStep5Body: "हर generated PDF browser history (IndexedDB) में auto-save होती है, download/view/delete support के साथ।",
      },
    },
    history: {
      en: {
        pageTitle: "History | SnapID.Pro",
        historyEyebrow: "History Vault",
        historyHeading: "Your Generated PDF History",
        historyIntro: "Stored in IndexedDB locally in your browser. No app-imposed limit.",
        clearAll: "Clear All History",
        itemSaved: "item(s) saved",
        emptyTitle: "No history yet",
        emptyBody: "Generate a PDF from the main page and it will appear here automatically.",
        goGenerator: "Go to Generator",
        pdfPreview: "PDF Preview",
        close: "Close",
        size: "Size:",
        photos: "Photos:",
        dpi: "DPI:",
        sheet: "Sheet:",
        bg: "BG:",
        view: "View",
        download: "Download",
        delete: "Delete",
        clearConfirm: "Clear entire history? This cannot be undone.",
      },
      ne: {
        pageTitle: "इतिहास | SnapID.Pro",
        historyEyebrow: "History Vault",
        historyHeading: "तपाईंको Generated PDF History",
        historyIntro: "तपाईंको browser मा IndexedDB भित्र locally stored। App-imposed limit छैन।",
        clearAll: "सबै History हटाउनुहोस्",
        itemSaved: "item(s) saved",
        emptyTitle: "अहिले history छैन",
        emptyBody: "Main page बाट PDF generate गरेपछि यहाँ automatic देखिन्छ।",
        goGenerator: "Generator मा जानुहोस्",
        pdfPreview: "PDF Preview",
        close: "बन्द गर्नुहोस्",
        size: "Size:",
        photos: "Photos:",
        dpi: "DPI:",
        sheet: "Sheet:",
        bg: "BG:",
        view: "हेर्नुहोस्",
        download: "Download",
        delete: "Delete",
        clearConfirm: "पूरै history clear गर्ने? यो undo गर्न मिल्दैन।",
      },
      hi: {
        pageTitle: "इतिहास | SnapID.Pro",
        historyEyebrow: "History Vault",
        historyHeading: "आपकी Generated PDF History",
        historyIntro: "आपके browser में IndexedDB के अंदर locally stored। App-imposed limit नहीं है।",
        clearAll: "सारी History हटाएं",
        itemSaved: "item(s) saved",
        emptyTitle: "अभी history नहीं है",
        emptyBody: "Main page से PDF generate करें, वह यहां automatically दिखेगी।",
        goGenerator: "Generator पर जाएं",
        pdfPreview: "PDF Preview",
        close: "बंद करें",
        size: "Size:",
        photos: "Photos:",
        dpi: "DPI:",
        sheet: "Sheet:",
        bg: "BG:",
        view: "View",
        download: "Download",
        delete: "Delete",
        clearConfirm: "पूरी history clear करें? इसे undo नहीं किया जा सकता।",
      },
    },
  };

  function getPageName() {
    const declaredPage = document.body.getAttribute("data-page");
    if (declaredPage) return declaredPage;
    const pathPage = window.location.pathname.replace(/^\/+|\/+$/g, "");
    return pathPage || "common";
  }

  function normalizeLang(lang) {
    return supported.includes(lang) ? lang : "en";
  }

  function getInitialLang() {
    const saved = localStorage.getItem(LANG_KEY);
    if (supported.includes(saved)) return saved;
    const browserLang = (navigator.language || "").toLowerCase();
    if (browserLang.startsWith("ne")) return "ne";
    if (browserLang.startsWith("hi")) return "hi";
    return "en";
  }

  function packFor(lang) {
    const page = getPageName();
    return {
      ...(common.en || {}),
      ...((pages[page] && pages[page].en) || {}),
      ...(common[lang] || {}),
      ...((pages[page] && pages[page][lang]) || {}),
    };
  }

  function t(key, vars) {
    const pack = packFor(window.SNAP_PAGE_LANG || getInitialLang());
    const template = pack[key] || key;
    return String(template).replace(/\{(\w+)\}/g, (_, name) => (
      vars && Object.prototype.hasOwnProperty.call(vars, name) ? vars[name] : `{${name}}`
    ));
  }

  function applyLanguage(lang) {
    const normalized = normalizeLang(lang);
    window.SNAP_PAGE_LANG = normalized;
    localStorage.setItem(LANG_KEY, normalized);
    document.documentElement.setAttribute("lang", normalized);

    const pack = packFor(normalized);
    document.querySelectorAll("[data-i18n]").forEach((el) => {
      const key = el.getAttribute("data-i18n");
      if (pack[key]) el.textContent = pack[key];
    });
    document.querySelectorAll("[data-i18n-title]").forEach((el) => {
      const key = el.getAttribute("data-i18n-title");
      if (pack[key]) el.setAttribute("title", pack[key]);
    });
    document.querySelectorAll("[data-i18n-aria]").forEach((el) => {
      const key = el.getAttribute("data-i18n-aria");
      if (pack[key]) el.setAttribute("aria-label", pack[key]);
    });

    if (pack.pageTitle) document.title = pack.pageTitle;
    const toggle = document.getElementById("langToggle");
    if (toggle) {
      toggle.textContent = pack.langShort;
      toggle.title = pack.switchLanguage;
      toggle.setAttribute("aria-label", pack.switchLanguage);
    }

    window.dispatchEvent(new CustomEvent("snapid:languagechange", { detail: { lang: normalized } }));
  }

  function init() {
    const toggle = document.getElementById("langToggle");
    if (toggle) {
      toggle.addEventListener("click", () => {
        const index = supported.indexOf(window.SNAP_PAGE_LANG || getInitialLang());
        applyLanguage(supported[(index + 1) % supported.length]);
      });
    }
    applyLanguage(getInitialLang());
  }

  window.SNAP_I18N = { applyLanguage, t, supported };
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
