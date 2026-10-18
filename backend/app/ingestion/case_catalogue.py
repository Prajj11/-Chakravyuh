"""Synthetic exercise specifications. Pattern names are generation metadata, never features."""

from dataclasses import dataclass


@dataclass(frozen=True)
class DemoCase:
    slug: str
    city: str
    lat: float
    lon: float
    title: str
    pattern: str
    en: str
    hi: str
    hinglish: str

    @property
    def scenario_id(self) -> str:
        return "demo_" + self.slug


CASES = (
    DemoCase(
        "flood_photo",
        "Mumbai",
        19.076,
        72.8777,
        "Recycled flood photograph",
        "synchronized",
        "A photograph is circulating as today's Mumbai station flood. The "
        "caption says every train is cancelled.",
        "एक तस्वीर को आज मुंबई स्टेशन की बाढ़ बताया जा रहा है। संदेश में सभी रेलगाड़ियाँ रद्द होने का दावा है।",
        "Ek photo ko aaj Mumbai station ki baadh bataya ja raha hai. Caption"
        " kehta hai sab trains cancel hain.",
    ),
    DemoCase(
        "school_heat",
        "Delhi",
        28.6139,
        77.209,
        "Unverified school closure notice",
        "staggered",
        "A forwarded Delhi heat notice claims all schools will close for the"
        " entire month. The notice has no issuing office.",
        "दिल्ली में गर्मी का एक साझा संदेश पूरे महीने स्कूल बंद रहने का दावा"
        " करता है। जारी करने वाले कार्यालय का नाम नहीं है।",
        "Delhi ka forwarded heat notice poore mahine schools band hone ka "
        "daava karta hai. Issuing office ka naam nahi hai.",
    ),
    DemoCase(
        "metro_fare",
        "Bengaluru",
        12.9716,
        77.5946,
        "Altered metro fare screenshot",
        "mixed",
        "A Bengaluru metro screenshot claims fares will triple tomorrow. The"
        " cropped image omits its date and source.",
        "बेंगलुरु मेट्रो के एक स्क्रीनशॉट में कल किराया तीन गुना होने का "
        "दावा है। तस्वीर में तारीख और स्रोत नहीं दिखते।",
        "Bengaluru metro screenshot mein kal fare teen guna hone ka daava "
        "hai. Cropped image mein date aur source nahi hain.",
    ),
    DemoCase(
        "water_notice",
        "Chennai",
        13.0827,
        80.2707,
        "Unverified water contamination claim",
        "synchronized",
        "A Chennai water message claims every neighbourhood supply is "
        "contaminated. It cites an unnamed laboratory.",
        "चेन्नई के पानी से जुड़े संदेश में हर इलाके की आपूर्ति दूषित होने का"
        " दावा है। प्रयोगशाला का नाम नहीं दिया गया है।",
        "Chennai water message har area ki supply contaminated hone ka daava"
        " karta hai. Laboratory ka naam nahi diya hai.",
    ),
    DemoCase(
        "bank_queue",
        "Kolkata",
        22.5726,
        88.3639,
        "Fictional bank closure rumour",
        "staggered",
        "A Kolkata post claims the fictional Example Community Bank will "
        "freeze all withdrawals tomorrow. No official notice is linked.",
        "कोलकाता की पोस्ट में काल्पनिक उदाहरण सामुदायिक बैंक द्वारा कल सभी "
        "निकासी रोकने का दावा है। आधिकारिक सूचना का लिंक नहीं है।",
        "Kolkata post mein fictional Example Community Bank kal withdrawals "
        "rokne ka daava hai. Official notice ka link nahi hai.",
    ),
    DemoCase(
        "clinic_message",
        "Hyderabad",
        17.385,
        78.4867,
        "Misattributed clinic message",
        "mixed",
        "A Hyderabad clinic message attributes a blanket vaccine ban to an "
        "unnamed doctor. The forwarded text provides no medical source.",
        "हैदराबाद के क्लिनिक संदेश में एक अनाम डॉक्टर के नाम पर सभी टीकों पर"
        " प्रतिबंध का दावा है। चिकित्सा स्रोत नहीं दिया गया है।",
        "Hyderabad clinic message ek unnamed doctor ke naam par sab vaccines"
        " ban hone ka daava karta hai. Medical source nahi hai.",
    ),
    DemoCase(
        "exam_paper",
        "Jaipur",
        26.9124,
        75.7873,
        "Fictional exam paper leak",
        "synchronized",
        "A Jaipur group advertises a leaked paper for the fictional Example "
        "Scholarship exam. Every advertisement links the same unverified "
        "page.",
        "जयपुर का एक समूह काल्पनिक उदाहरण छात्रवृत्ति परीक्षा का प्रश्नपत्र "
        "लीक होने का विज्ञापन कर रहा है। सभी संदेश एक ही अप्रमाणित पेज से "
        "जुड़े हैं।",
        "Jaipur group fictional Example Scholarship exam ka leaked paper "
        "advertise karta hai. Sab messages ek hi unverified page se jude "
        "hain.",
    ),
    DemoCase(
        "power_refund",
        "Ahmedabad",
        23.0225,
        72.5714,
        "Impersonated electricity refund",
        "mixed",
        "An Ahmedabad electricity refund message asks residents to use a "
        "fictional claim portal. The message has no verifiable provider "
        "notice.",
        "अहमदाबाद बिजली रिफंड संदेश लोगों से एक काल्पनिक दावा पोर्टल "
        "इस्तेमाल करने को कहता है। प्रदाता की सत्यापित सूचना उपलब्ध नहीं है।",
        "Ahmedabad electricity refund message fictional claim portal use "
        "karne ko kehta hai. Provider ka verified notice available nahi hai.",
    ),
    DemoCase(
        "fuel_shortage",
        "Pune",
        18.5204,
        73.8567,
        "Fuel shortage amplification",
        "synchronized",
        "A Pune fuel post claims every filling station will close for a "
        "week. Repeated messages cite the same anonymous screenshot.",
        "पुणे की ईंधन पोस्ट में सभी पेट्रोल पंप एक सप्ताह बंद रहने का दावा "
        "है। बार-बार साझा संदेश एक ही अनाम स्क्रीनशॉट दिखाते हैं।",
        "Pune fuel post sab filling stations ek hafte band hone ka daava "
        "karta hai. Repeated messages wahi anonymous screenshot dikhate "
        "hain.",
    ),
    DemoCase(
        "cyclone_voice",
        "Kochi",
        9.9312,
        76.2673,
        "Unverified cyclone voice-message transcript",
        "staggered",
        "A Kochi voice-message transcript claims a cyclone warning covers "
        "the whole city tonight. The speaker and original recording are "
        "unavailable.",
        "कोच्चि के आवाज संदेश के लिखित रूप में आज रात पूरे शहर के लिए "
        "चक्रवात चेतावनी का दावा है। वक्ता और मूल रिकॉर्डिंग उपलब्ध नहीं "
        "हैं।",
        "Kochi voice-message transcript aaj raat poore shehar ke cyclone "
        "warning ka daava karta hai. Speaker aur original recording "
        "available nahi hain.",
    ),
    DemoCase(
        "beach_restriction",
        "Panaji",
        15.4909,
        73.8278,
        "Outdated beach restriction notice",
        "mixed",
        "A Panaji travel page recirculates an undated beach restriction "
        "notice as a new order. Travellers are asking for the issuing date.",
        "पणजी का यात्रा पेज बिना तारीख वाला समुद्र तट प्रतिबंध संदेश नया "
        "आदेश बताकर साझा कर रहा है। यात्री जारी होने की तारीख पूछ रहे हैं।",
        "Panaji travel page bina date ka beach restriction notice naya order"
        " batakar share karta hai. Travellers issue date pooch rahe hain.",
    ),
    DemoCase(
        "ration_registration",
        "Bhopal",
        23.2599,
        77.4126,
        "Fictional ration registration deadline",
        "synchronized",
        "A Bhopal ration message claims benefits stop tonight unless "
        "residents register on a fictional website. No department reference "
        "is supplied.",
        "भोपाल राशन संदेश में काल्पनिक वेबसाइट पर पंजीकरण न करने पर आज रात "
        "लाभ बंद होने का दावा है। विभाग का संदर्भ नहीं दिया गया है।",
        "Bhopal ration message fictional website par registration na karne "
        "se aaj raat benefits band hone ka daava karta hai. Department "
        "reference nahi hai.",
    ),
    DemoCase(
        "bridge_clip",
        "Patna",
        25.5941,
        85.1376,
        "Mislocated bridge clip caption",
        "staggered",
        "A Patna caption describes an unavailable bridge video as a collapse"
        " this morning. The caption does not establish the recording "
        "location.",
        "पटना के संदेश में अनुपलब्ध पुल वीडियो को आज सुबह की दुर्घटना बताया "
        "गया है। संदेश से रिकॉर्डिंग का स्थान स्थापित नहीं होता।",
        "Patna caption ek unavailable bridge video ko aaj subah ka collapse "
        "batata hai. Recording location establish nahi hoti.",
    ),
    DemoCase(
        "evacuation_route",
        "Bhubaneswar",
        20.2961,
        85.8245,
        "Conflicting evacuation route messages",
        "mixed",
        "A Bhubaneswar evacuation message points everyone toward a fictional"
        " shelter while another post disputes the route. Neither includes a "
        "current advisory.",
        "भुवनेश्वर के निकासी संदेश में सभी को काल्पनिक आश्रय की ओर भेजा गया "
        "है और दूसरी पोस्ट मार्ग पर सवाल उठाती है। वर्तमान सलाह संलग्न नहीं "
        "है।",
        "Bhubaneswar evacuation message sabko fictional shelter bhejta hai "
        "aur doosri post route par sawaal karti hai. Current advisory "
        "attached nahi hai.",
    ),
    DemoCase(
        "telecom_shutdown",
        "Guwahati",
        26.1445,
        91.7362,
        "Telecom shutdown rumour",
        "synchronized",
        "A Guwahati forward claims all mobile networks will shut down at "
        "midnight. Its alleged order number cannot be checked from the "
        "message.",
        "गुवाहाटी के साझा संदेश में आधी रात से सभी मोबाइल नेटवर्क बंद होने "
        "का दावा है। दिए गए आदेश नंबर की संदेश से जाँच नहीं हो सकती।",
        "Guwahati forward aadhi raat se sab mobile networks band hone ka "
        "daava karta hai. Order number message se verify nahi hota.",
    ),
    DemoCase(
        "polling_hours",
        "Lucknow",
        26.8467,
        80.9462,
        "Fictional polling-hours change",
        "mixed",
        "A Lucknow election graphic claims polling hours changed for the "
        "fictional Example Ward exercise. No dated election notice "
        "accompanies it.",
        "लखनऊ के चुनाव चित्र में काल्पनिक उदाहरण वार्ड अभ्यास के मतदान समय "
        "में बदलाव का दावा है। तारीख वाली चुनाव सूचना संलग्न नहीं है।",
        "Lucknow election graphic fictional Example Ward exercise ke polling"
        " hours badalne ka daava karta hai. Dated election notice attached "
        "nahi hai.",
    ),
    DemoCase(
        "blood_donation",
        "Surat",
        21.1702,
        72.8311,
        "Volunteer blood donation mobilisation",
        "mobilization",
        "Surat volunteers share a fictional blood donation event schedule. "
        "Participants are asked to confirm eligibility with the organising "
        "clinic.",
        "सूरत के स्वयंसेवक काल्पनिक रक्तदान कार्यक्रम की समय-सारणी साझा कर "
        "रहे हैं। पात्रता की पुष्टि आयोजक क्लिनिक से करने को कहा गया है।",
        "Surat volunteers fictional blood donation event schedule share kar "
        "rahe hain. Eligibility organising clinic se confirm karein.",
    ),
    DemoCase(
        "cleanup_drive",
        "Indore",
        22.7196,
        75.8577,
        "Neighbourhood cleanup coordination",
        "mobilization",
        "Indore neighbours coordinate a fictional park cleanup. The shared "
        "checklist covers gloves, collection bags and a meeting time.",
        "इंदौर के पड़ोसी काल्पनिक पार्क सफाई कार्यक्रम का समन्वय कर रहे हैं।"
        " सूची में दस्ताने, कचरे के थैले और मिलने का समय है।",
        "Indore neighbours fictional park cleanup coordinate kar rahe hain. "
        "Checklist mein gloves, bags aur meeting time hain.",
    ),
    DemoCase(
        "food_volunteers",
        "Nagpur",
        21.1458,
        79.0882,
        "Food collection volunteer network",
        "mobilization",
        "Nagpur volunteers repeat a fictional food collection schedule. "
        "Posts request sealed supplies and a check with the local "
        "coordinator.",
        "नागपुर के स्वयंसेवक काल्पनिक खाद्य संग्रह समय-सारणी साझा कर रहे "
        "हैं। बंद पैकेट और स्थानीय समन्वयक से पुष्टि की माँग है।",
        "Nagpur volunteers fictional food collection schedule repeat kar "
        "rahe hain. Sealed supplies aur local coordinator se confirmation "
        "chahiye.",
    ),
    DemoCase(
        "storm_help",
        "Thiruvananthapuram",
        8.5241,
        76.9366,
        "Storm assistance coordination",
        "mobilization",
        "Thiruvananthapuram residents share a fictional storm assistance "
        "roster. Volunteers coordinate transport and ask readers to check "
        "current local advisories.",
        "तिरुवनंतपुरम के निवासी काल्पनिक तूफान सहायता सूची साझा कर रहे हैं। "
        "स्वयंसेवक परिवहन समन्वय और स्थानीय सलाह की जाँच करने को कहते हैं।",
        "Thiruvananthapuram residents fictional storm assistance roster "
        "share kar rahe hain. Volunteers transport coordinate karte hain aur"
        " local advisories check karne ko kehte hain.",
    ),
    DemoCase(
        "bus_feedback",
        "Chandigarh",
        30.7333,
        76.7794,
        "Independent bus service feedback",
        "organic",
        "Chandigarh residents discuss bus service experiences, waiting times"
        " and possible improvements at local stops.",
        "चंडीगढ़ के निवासी बस सेवा के अनुभव, प्रतीक्षा समय और स्थानीय स्टॉप पर संभावित सुधार पर चर्चा कर रहे हैं।",
        "Chandigarh residents bus service experiences, waiting time aur "
        "local stops ke improvements discuss kar rahe hain.",
    ),
    DemoCase(
        "park_access",
        "Dehradun",
        30.3165,
        78.0322,
        "Independent park access discussion",
        "organic",
        "Dehradun walkers discuss park access, shade and opening times based"
        " on separate neighbourhood observations.",
        "देहरादून के लोग अलग-अलग इलाकों के अनुभवों के आधार पर पार्क में "
        "प्रवेश, छाया और खुलने के समय की चर्चा कर रहे हैं।",
        "Dehradun walkers alag neighbourhood observations se park access, "
        "shade aur opening times discuss kar rahe hain.",
    ),
    DemoCase(
        "waste_pickup",
        "Ranchi",
        23.3441,
        85.3096,
        "Waste collection observations",
        "organic",
        "Ranchi residents compare household waste collection schedules and "
        "report different experiences on their streets.",
        "रांची के निवासी घरेलू कचरा संग्रह समय-सारणी की तुलना और अपनी गलियों के अलग-अलग अनुभव साझा कर रहे हैं।",
        "Ranchi residents household waste collection schedules compare karte"
        " hain aur apni streets ke alag experiences share karte hain.",
    ),
    DemoCase(
        "harbour_weather",
        "Visakhapatnam",
        17.6868,
        83.2185,
        "Harbour weather discussion",
        "organic",
        "Visakhapatnam harbour visitors discuss changing weather and compare"
        " their own observations with dated public bulletins.",
        "विशाखापत्तनम बंदरगाह के लोग बदलते मौसम पर चर्चा और अपने अनुभवों की "
        "तारीख वाले सार्वजनिक बुलेटिन से तुलना कर रहे हैं।",
        "Visakhapatnam harbour visitors changing weather discuss karte hain "
        "aur apne observations dated public bulletins se compare karte hain.",
    ),
    DemoCase(
        "library_hours",
        "Coimbatore",
        11.0168,
        76.9558,
        "Library opening-hours discussion",
        "organic",
        "Coimbatore readers discuss library opening hours, available books "
        "and study space using independent visits as context.",
        "कोयंबटूर के पाठक अलग-अलग यात्राओं के आधार पर पुस्तकालय के समय, "
        "उपलब्ध किताबों और पढ़ने की जगह पर चर्चा कर रहे हैं।",
        "Coimbatore readers independent visits se library opening hours, "
        "books aur study space discuss kar rahe hain.",
    ),
)

CASE_BY_ID = {case.scenario_id: case for case in CASES}
DEMO_CASE_IDS = tuple(CASE_BY_ID)
POSTS_PER_CASE = 300
