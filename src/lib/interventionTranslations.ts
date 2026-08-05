import type { Language } from "../context/LanguageContext";

/**
 * Multilingual intervention system — static, instant translations for the
 * two pieces of intervention-card text that are fixed per lever
 * (`LEVER_HEADLINES` in `backend/agents/intervention.py` and the action
 * button label built in `interventionContent.ts`). No network call, no
 * latency, never wrong because it's hand-authored, not inferred.
 *
 * The third piece — `rationale` — is often LLM-personalised per session and
 * can't be covered by a static table; see `useTranslatedRationale.ts` for how
 * that gets a real (Groq-backed) translation instead, with `fallbackRationale`
 * below as the always-available instant placeholder while that loads.
 */

interface LeverTranslation {
  headline: string;
  actionLabel: string;
  fallbackRationale: string;
}

type Catalog = Record<string, Partial<Record<Exclude<Language, "en">, LeverTranslation>>>;

export const LEVER_TRANSLATIONS: Catalog = {
  free_delivery_waiver: {
    hi: { headline: "मुफ़्त डिलीवरी, हमारी ओर से — अभी चेकआउट करें", actionLabel: "मुफ़्त डिलीवरी लागू करें", fallbackRationale: "इस ऑर्डर पर डिलीवरी शुल्क माफ़ किया जा रहा है।" },
    ta: { headline: "இலவச டெலிவரி — இப்போது செக்அவுட் செய்யவும்", actionLabel: "இலவச டெலிவரியைப் பயன்படுத்தவும்", fallbackRationale: "இந்த ஆர்டருக்கு டெலிவரி கட்டணம் தள்ளுபடி செய்யப்படுகிறது." },
  },
  targeted_discount_code: {
    hi: { headline: "यह रहा आपके कार्ट के लिए एक खास डिस्काउंट कोड", actionLabel: "डिस्काउंट पाएं", fallbackRationale: "इस कार्ट के लिए एक व्यक्तिगत डिस्काउंट कोड जारी किया गया है।" },
    ta: { headline: "உங்கள் கார்ட்டுக்கான தனி தள்ளுபடி குறியீடு", actionLabel: "தள்ளுபடியைப் பெறுங்கள்", fallbackRationale: "இந்த கார்ட்டுக்கு தனிப்பட்ட தள்ளுபடி குறியீடு வழங்கப்பட்டுள்ளது." },
  },
  emi_plan_highlight: {
    hi: { headline: "इसे आसान नो-कॉस्ट EMI में बदलें", actionLabel: "EMI विकल्प देखें", fallbackRationale: "बिना किसी अतिरिक्त लागत के आसान मासिक किस्तों में भुगतान करें।" },
    ta: { headline: "இதை எளிதான நோ-காஸ்ட் EMI ஆக மாற்றுங்கள்", actionLabel: "EMI விருப்பங்களைப் பார்க்கவும்", fallbackRationale: "கூடுதல் செலவு இல்லாமல் மாத தவணைகளில் செலுத்தலாம்." },
  },
  price_drop_alert: {
    hi: { headline: "कीमत गिरते ही हम आपको बताएंगे", actionLabel: "प्राइस हिस्ट्री देखें", fallbackRationale: "इस उत्पाद की कीमत में गिरावट की सूचना आपको दी जाएगी।" },
    ta: { headline: "விலை குறையும் போது உங்களுக்குத் தெரிவிப்போம்", actionLabel: "விலை வரலாற்றைப் பார்க்கவும்", fallbackRationale: "இந்த பொருளின் விலை குறைந்தால் உங்களுக்கு அறிவிக்கப்படும்." },
  },
  delivery_speed_upgrade: {
    hi: { headline: "जल्दी पाएं — अपना डिलीवरी स्लॉट अपग्रेड करें", actionLabel: "डिलीवरी अपग्रेड करें", fallbackRationale: "तेज़ डिलीवरी स्लॉट मुफ़्त या रियायती दर पर उपलब्ध है।" },
    ta: { headline: "வேகமாகப் பெறுங்கள் — டெலிவரி நேரத்தை மேம்படுத்துங்கள்", actionLabel: "டெலிவரியை மேம்படுத்தவும்", fallbackRationale: "வேகமான டெலிவரி இலவசமாகவோ அல்லது தள்ளுபடியிலோ கிடைக்கிறது." },
  },
  trust_badge_reassurance: {
    hi: { headline: "100% सुरक्षित भुगतान और आसान रिटर्न", actionLabel: "विवरण देखें", fallbackRationale: "सुरक्षित भुगतान, वापसी नीति और असली उत्पाद की गारंटी दी जाती है।" },
    ta: { headline: "100% பாதுகாப்பான பணம் செலுத்துதல் & எளிதான திரும்பப் பெறுதல்", actionLabel: "விவரங்களைப் பார்க்கவும்", fallbackRationale: "பாதுகாப்பான கட்டணம், திரும்பப் பெறும் உத்தரவாதம் வழங்கப்படுகிறது." },
  },
  guest_to_account_nudge: {
    hi: { headline: "एक टैप में अकाउंट बनाएं और ऑर्डर ट्रैक करें", actionLabel: "अकाउंट बनाएं", fallbackRationale: "अकाउंट बनाने से ऑर्डर ट्रैकिंग और तेज़ रीऑर्डर आसान हो जाता है।" },
    ta: { headline: "ஒரு தட்டில் கணக்கை உருவாக்கி ஆர்டரைக் கண்காணிக்கவும்", actionLabel: "கணக்கை உருவாக்கவும்", fallbackRationale: "கணக்கு உருவாக்குவதால் ஆர்டர் கண்காணிப்பு எளிதாகிறது." },
  },
  saved_payment_prompt: {
    hi: { headline: "तेज़ चेकआउट के लिए भुगतान का तरीका सेव करें", actionLabel: "पेमेंट सेव करें", fallbackRationale: "भुगतान विवरण सेव करने से चेकआउट का सबसे कठिन चरण हट जाता है।" },
    ta: { headline: "வேகமான செக்அவுட்டுக்கு பணம் செலுத்தும் முறையைச் சேமிக்கவும்", actionLabel: "பணம் செலுத்தும் முறையைச் சேமிக்கவும்", fallbackRationale: "கட்டண விவரத்தைச் சேமிப்பது செக்அவுட்டை எளிதாக்கும்." },
  },
  review_summary_surface: {
    hi: { headline: "देखें अन्य खरीदार वास्तव में क्या सोचते हैं", actionLabel: "AI सारांश पढ़ें", fallbackRationale: "समीक्षाओं का एक AI सारांश आपके संदेह दूर करने के लिए दिखाया गया है।" },
    ta: { headline: "மற்ற வாங்குபவர்கள் உண்மையில் என்ன நினைக்கிறார்கள் என்று பாருங்கள்", actionLabel: "AI சுருக்கத்தைப் படிக்கவும்", fallbackRationale: "மதிப்புரைகளின் AI சுருக்கம் உங்கள் சந்தேகத்தைத் தீர்க்கக் காட்டப்படுகிறது." },
  },
  stock_scarcity_nudge: {
    hi: { headline: "स्टॉक लगभग खत्म — इससे पहले कि यह चला जाए, इसे ले लें", actionLabel: "मिलते-जुलते आइटम देखें", fallbackRationale: "इस उत्पाद की मांग ज़्यादा है और स्टॉक सीमित है।" },
    ta: { headline: "ஸ்டாக் தீர்ந்துவிடும் முன் வாங்குங்கள்", actionLabel: "ஒத்த பொருட்களைப் பார்க்கவும்", fallbackRationale: "இந்த பொருளுக்கு தேவை அதிகம், ஸ்டாக் குறைவாக உள்ளது." },
  },
  exit_intent_reminder: {
    hi: { headline: "अभी भी सोच रहे हैं? आपका कार्ट सेव है", actionLabel: "कार्ट देखें", fallbackRationale: "आपका कार्ट सेव कर लिया गया है, जब चाहें लौट सकते हैं।" },
    ta: { headline: "இன்னும் யோசிக்கிறீர்களா? உங்கள் கார்ட் சேமிக்கப்பட்டுள்ளது", actionLabel: "கார்ட்டைப் பார்க்கவும்", fallbackRationale: "உங்கள் கார்ட் பாதுகாப்பாக சேமிக்கப்பட்டுள்ளது." },
  },
  abandoned_cart_email: {
    hi: { headline: "हम बाद में आपको इस कार्ट की याद दिलाएंगे", actionLabel: "ठीक है", fallbackRationale: "सत्र समाप्त होने के बाद एक फॉलो-अप याद दिलाया जाएगा।" },
    ta: { headline: "இந்த கார்ட்டை பின்னர் உங்களுக்கு நினைவூட்டுவோம்", actionLabel: "சரி", fallbackRationale: "அமர்வு முடிந்த பிறகு நினைவூட்டல் அனுப்பப்படும்." },
  },
  checkout_assist_chat: {
    hi: { headline: "मदद चाहिए? अभी हमसे चैट करें", actionLabel: "AI सहायक से चैट करें", fallbackRationale: "चेकआउट के बीच में लाइव सहायता उपलब्ध है।" },
    ta: { headline: "உதவி தேவையா? இப்போது எங்களுடன் அரட்டையடிக்கவும்", actionLabel: "AI உதவியாளருடன் அரட்டையடிக்கவும்", fallbackRationale: "செக்அவுட்டின் போது நேரடி உதவி கிடைக்கிறது." },
  },
  payment_retry_help: {
    hi: { headline: "भुगतान नहीं हुआ — दूसरा तरीका आज़माएं", actionLabel: "AI सहायक से चैट करें", fallbackRationale: "भुगतान विफल हो गया; कोई दूसरा तरीका आज़माने का सुझाव है।" },
    ta: { headline: "பணம் செலுத்தல் தோல்வியடைந்தது — வேறு முறையை முயற்சிக்கவும்", actionLabel: "AI உதவியாளருடன் அரட்டையடிக்கவும்", fallbackRationale: "பணம் செலுத்தல் தோல்வியடைந்தது; வேறு முறையை முயற்சிக்கவும்." },
  },
};

const UI_STRINGS: Record<Exclude<Language, "en">, { accept: string; dismiss: string; whySeeing: string; aiSuggested: string }> = {
  hi: { accept: "स्वीकार करें", dismiss: "खारिज करें", whySeeing: "यह क्यों दिख रहा है?", aiSuggested: "✨ आपके सत्र के लिए AI-सुझाव" },
  ta: { accept: "ஏற்கவும்", dismiss: "நிராகரிக்கவும்", whySeeing: "இது ஏன் காட்டப்படுகிறது?", aiSuggested: "✨ உங்கள் அமர்வுக்கான AI பரிந்துரை" },
};

export function translateHeadline(leverId: string, englishHeadline: string, language: Language): string {
  if (language === "en") return englishHeadline;
  return LEVER_TRANSLATIONS[leverId]?.[language]?.headline ?? englishHeadline;
}

export function translateActionLabel(leverId: string, englishLabel: string, language: Language): string {
  if (language === "en") return englishLabel;
  return LEVER_TRANSLATIONS[leverId]?.[language]?.actionLabel ?? englishLabel;
}

export function fallbackRationale(leverId: string, language: Language): string | null {
  if (language === "en") return null;
  return LEVER_TRANSLATIONS[leverId]?.[language]?.fallbackRationale ?? null;
}

export function uiString(key: keyof (typeof UI_STRINGS)["hi"], language: Language): string {
  if (language === "en") {
    return { accept: "Accept", dismiss: "Dismiss", whySeeing: "Why am I seeing this?", aiSuggested: "✨ AI-suggested for your session" }[key];
  }
  return UI_STRINGS[language][key];
}
