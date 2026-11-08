"""Fixed farmer-facing messages in English (en), Hindi (hi) and Punjabi (pa).
These are short safety/status sentences, written once and stored in code. They are first drafts: have a native speaker
(ideally an agricultural extension worker) review them before launch. Disease advice itself lives in the `advisories`
table (see advisories.py), not here."""

LANGS = ("en", "hi", "pa")
LANG_NAMES = {"en": "English", "hi": "हिन्दी", "pa": "ਪੰਜਾਬੀ"}

TEXT: dict[str, dict[str, str]] = {
    "healthy": {
        "en": "No disease seen on this {crop} leaf. It looks healthy. Keep monitoring.",
        "hi": "इस {crop} के पत्ते पर कोई रोग नहीं दिखा। यह स्वस्थ लगता है। निगरानी जारी रखें।",
        "pa": "ਇਸ {crop} ਦੇ ਪੱਤੇ ਉੱਤੇ ਕੋਈ ਬਿਮਾਰੀ ਨਹੀਂ ਦਿਸੀ। ਇਹ ਸਿਹਤਮੰਦ ਲੱਗਦਾ ਹੈ। ਨਿਗਰਾਨੀ ਜਾਰੀ ਰੱਖੋ।",
    },
    "likely": {
        "en": "This is a possible match, not a confirmed diagnosis. An expert will review it.",
        "hi": "यह एक संभावित मिलान है, पक्का निदान नहीं। कृषि विशेषज्ञ इसकी जाँच करेंगे।",
        "pa": "ਇਹ ਸੰਭਾਵੀ ਮੇਲ ਹੈ, ਪੱਕਾ ਨਿਦਾਨ ਨਹੀਂ। ਖੇਤੀਬਾੜੀ ਮਾਹਿਰ ਇਸ ਦੀ ਜਾਂਚ ਕਰਨਗੇ।",
    },
    "interim": {
        "en": "Until an expert confirms: separate the affected plants if you can, avoid watering the leaves from above, "
              "and do not spray anything before checking with your local Krishi Vigyan Kendra (KVK).",
        "hi": "विशेषज्ञ की पुष्टि तक: प्रभावित पौधों को अलग करें, पत्तियों पर ऊपर से पानी न दें, और अपने स्थानीय "
              "कृषि विज्ञान केंद्र (KVK) से पूछे बिना कोई छिड़काव न करें।",
        "pa": "ਮਾਹਿਰ ਦੀ ਪੁਸ਼ਟੀ ਤੱਕ: ਪ੍ਰਭਾਵਿਤ ਪੌਦਿਆਂ ਨੂੰ ਵੱਖ ਕਰੋ, ਪੱਤਿਆਂ ਉੱਤੇ ਉੱਪਰੋਂ ਪਾਣੀ ਨਾ ਦਿਓ, ਅਤੇ ਆਪਣੇ ਸਥਾਨਕ "
              "ਕ੍ਰਿਸ਼ੀ ਵਿਗਿਆਨ ਕੇਂਦਰ (KVK) ਨਾਲ ਸਲਾਹ ਕੀਤੇ ਬਿਨਾਂ ਕੋਈ ਛਿੜਕਾਅ ਨਾ ਕਰੋ।",
    },
    "hint_crop_not_selected": {
        "en": "Choose your crop before uploading for a more reliable result.",
        "hi": "अधिक भरोसेमंद नतीजे के लिए अपलोड करने से पहले अपनी फसल चुनें।",
        "pa": "ਵਧੇਰੇ ਭਰੋਸੇਯੋਗ ਨਤੀਜੇ ਲਈ ਅਪਲੋਡ ਕਰਨ ਤੋਂ ਪਹਿਲਾਂ ਆਪਣੀ ਫ਼ਸਲ ਚੁਣੋ।",
    },
    "hint_poor_photo": {
        "en": "A sharper photo would give a more reliable result.",
        "hi": "ज़्यादा साफ़ फोटो से नतीजा अधिक भरोसेमंद होगा।",
        "pa": "ਵੱਧ ਸਾਫ਼ ਫ਼ੋਟੋ ਨਾਲ ਨਤੀਜਾ ਵਧੇਰੇ ਭਰੋਸੇਯੋਗ ਹੋਵੇਗਾ।",
    },
    "esc_unsupported_crop": {
        "en": "Our AI cannot assess {crop} yet, so your photo has been sent to an agricultural expert.",
        "hi": "हमारा AI अभी {crop} की जाँच नहीं कर सकता, इसलिए आपकी फोटो कृषि विशेषज्ञ को भेज दी गई है।",
        "pa": "ਸਾਡਾ AI ਅਜੇ {crop} ਦੀ ਜਾਂਚ ਨਹੀਂ ਕਰ ਸਕਦਾ, ਇਸ ਲਈ ਤੁਹਾਡੀ ਫ਼ੋਟੋ ਖੇਤੀਬਾੜੀ ਮਾਹਿਰ ਨੂੰ ਭੇਜ ਦਿੱਤੀ ਗਈ ਹੈ।",
    },
    "esc_low_confidence": {
        "en": "The AI is not sure about this photo, so it has been sent to an agricultural expert. "
              "A close-up photo of one leaf in good daylight can help.",
        "hi": "AI इस फोटो के बारे में पक्का नहीं है, इसलिए इसे कृषि विशेषज्ञ को भेज दिया गया है। "
              "दिन की रोशनी में एक पत्ते की नज़दीकी फोटो मदद करती है।",
        "pa": "AI ਨੂੰ ਇਸ ਫ਼ੋਟੋ ਬਾਰੇ ਯਕੀਨ ਨਹੀਂ ਹੈ, ਇਸ ਲਈ ਇਹ ਖੇਤੀਬਾੜੀ ਮਾਹਿਰ ਨੂੰ ਭੇਜ ਦਿੱਤੀ ਗਈ ਹੈ। "
              "ਦਿਨ ਦੀ ਰੌਸ਼ਨੀ ਵਿੱਚ ਇੱਕ ਪੱਤੇ ਦੀ ਨੇੜਿਓਂ ਫ਼ੋਟੋ ਮਦਦ ਕਰਦੀ ਹੈ।",
    },
    "esc_no_advice": {
        "en": "The AI found a possible problem but we have no verified advice for it yet, so an expert will review it.",
        "hi": "AI को संभावित समस्या मिली है, लेकिन इसके लिए अभी हमारे पास सत्यापित सलाह नहीं है, इसलिए विशेषज्ञ इसकी जाँच करेंगे।",
        "pa": "AI ਨੂੰ ਸੰਭਾਵੀ ਸਮੱਸਿਆ ਮਿਲੀ ਹੈ, ਪਰ ਇਸ ਲਈ ਸਾਡੇ ਕੋਲ ਅਜੇ ਪੜਤਾਲੀ ਸਲਾਹ ਨਹੀਂ ਹੈ, ਇਸ ਲਈ ਮਾਹਿਰ ਇਸ ਦੀ ਜਾਂਚ ਕਰਨਗੇ।",
    },
    "case_awaiting_review": {
        "en": "Your photo is waiting for an agricultural expert. The AI result below is preliminary. Check back later with this code.",
        "hi": "आपकी फोटो कृषि विशेषज्ञ की प्रतीक्षा में है। नीचे का AI नतीजा प्रारंभिक है। इस कोड से बाद में फिर देखें।",
        "pa": "ਤੁਹਾਡੀ ਫ਼ੋਟੋ ਖੇਤੀਬਾੜੀ ਮਾਹਿਰ ਦੀ ਉਡੀਕ ਵਿੱਚ ਹੈ। ਹੇਠਾਂ AI ਦਾ ਨਤੀਜਾ ਮੁੱਢਲਾ ਹੈ। ਇਸ ਕੋਡ ਨਾਲ ਬਾਅਦ ਵਿੱਚ ਫਿਰ ਦੇਖੋ।",
    },
    "case_under_review": {
        "en": "An agricultural expert is reviewing your case. The AI result below is preliminary.",
        "hi": "कृषि विशेषज्ञ आपके मामले की जाँच कर रहे हैं। नीचे का AI नतीजा प्रारंभिक है।",
        "pa": "ਖੇਤੀਬਾੜੀ ਮਾਹਿਰ ਤੁਹਾਡੇ ਕੇਸ ਦੀ ਜਾਂਚ ਕਰ ਰਹੇ ਹਨ। ਹੇਠਾਂ AI ਦਾ ਨਤੀਜਾ ਮੁੱਢਲਾ ਹੈ।",
    },
    "case_verified": {
        "en": "An agricultural expert has verified this case.",
        "hi": "कृषि विशेषज्ञ ने इस मामले की पुष्टि कर दी है।",
        "pa": "ਖੇਤੀਬਾੜੀ ਮਾਹਿਰ ਨੇ ਇਸ ਕੇਸ ਦੀ ਪੁਸ਼ਟੀ ਕਰ ਦਿੱਤੀ ਹੈ।",
    },
    "case_inconclusive": {
        "en": "The expert could not decide from this photo. Please upload a clearer photo, or contact your local Krishi Vigyan Kendra (KVK).",
        "hi": "विशेषज्ञ इस फोटो से निर्णय नहीं कर सके। कृपया साफ़ फोटो अपलोड करें या अपने स्थानीय कृषि विज्ञान केंद्र (KVK) से संपर्क करें।",
        "pa": "ਮਾਹਿਰ ਇਸ ਫ਼ੋਟੋ ਤੋਂ ਫ਼ੈਸਲਾ ਨਹੀਂ ਕਰ ਸਕੇ। ਕਿਰਪਾ ਕਰਕੇ ਸਾਫ਼ ਫ਼ੋਟੋ ਅਪਲੋਡ ਕਰੋ ਜਾਂ ਆਪਣੇ ਸਥਾਨਕ ਕ੍ਰਿਸ਼ੀ ਵਿਗਿਆਨ ਕੇਂਦਰ (KVK) ਨਾਲ ਸੰਪਰਕ ਕਰੋ।",
    },
    "expert_healthy": {
        "en": "The expert found no disease. Keep monitoring your plants.",
        "hi": "विशेषज्ञ को कोई रोग नहीं मिला। अपने पौधों की निगरानी करते रहें।",
        "pa": "ਮਾਹਿਰ ਨੂੰ ਕੋਈ ਬਿਮਾਰੀ ਨਹੀਂ ਮਿਲੀ। ਆਪਣੇ ਪੌਦਿਆਂ ਦੀ ਨਿਗਰਾਨੀ ਕਰਦੇ ਰਹੋ।",
    },
    "no_stored_advice": {
        "en": "No stored treatment advice for this disease yet. Please follow the expert's notes and contact your local Krishi Vigyan Kendra (KVK).",
        "hi": "इस रोग के लिए अभी कोई सहेजी हुई सलाह नहीं है। कृपया विशेषज्ञ के नोट्स का पालन करें और अपने स्थानीय कृषि विज्ञान केंद्र (KVK) से संपर्क करें।",
        "pa": "ਇਸ ਬਿਮਾਰੀ ਲਈ ਅਜੇ ਕੋਈ ਸੰਭਾਲੀ ਸਲਾਹ ਨਹੀਂ ਹੈ। ਕਿਰਪਾ ਕਰਕੇ ਮਾਹਿਰ ਦੇ ਨੋਟਾਂ ਦੀ ਪਾਲਣਾ ਕਰੋ ਅਤੇ ਆਪਣੇ ਸਥਾਨਕ ਕ੍ਰਿਸ਼ੀ ਵਿਗਿਆਨ ਕੇਂਦਰ (KVK) ਨਾਲ ਸੰਪਰਕ ਕਰੋ।",
    },
    "translation_pending": {
        "en": "",
        "hi": "आपकी भाषा में सत्यापित सलाह अभी उपलब्ध नहीं है; अंग्रेज़ी में दिखाई जा रही है।",
        "pa": "ਤੁਹਾਡੀ ਭਾਸ਼ਾ ਵਿੱਚ ਪੜਤਾਲੀ ਸਲਾਹ ਅਜੇ ਉਪਲਬਧ ਨਹੀਂ ਹੈ; ਅੰਗਰੇਜ਼ੀ ਵਿੱਚ ਦਿਖਾਈ ਜਾ ਰਹੀ ਹੈ।",
    },
}


def norm_lang(lang: str | None) -> str:
    lang = (lang or "en").strip().lower()[:2]
    return lang if lang in LANGS else "en"


def t(key: str, lang: str | None = "en", **fmt) -> str:
    text = TEXT[key][norm_lang(lang)] or TEXT[key]["en"]
    return text.format(**fmt) if fmt else text
