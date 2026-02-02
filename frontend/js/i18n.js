/**
 * Language Toggle System
 * Supports Arabic (ar) and English (en)
 * Stores preference in localStorage
 */

const i18n = {
    currentLang: localStorage.getItem('lang') || 'en',

    translations: {
        en: {
            // Navigation
            nav_mission: 'Our Mission',
            nav_impact: 'Impact',
            nav_campaigns: 'Campaigns',
            nav_contact: 'Contact',
            nav_donate: 'Donate Now',

            // Hero
            hero_title: 'End of the [night]<br>Begeting resilience',
            hero_subtitle: 'Fajr symbolizes the precise moment of clarity before the dawn. As the night ends, our mission begins. Rooted in the resilience of the olive tree, we bring strength and light to our communities.',
            hero_cta: 'SUPPORT OUR MISSION',
            hero_secondary: 'The Symbolism',

            // Alert bar
            alert_matching: 'URGENT: ALL GIFTS ARE CURRENTLY BEING MATCHED 2X — DOUBLE YOUR IMPACT TODAY',

            // Impact section
            impact_title: 'Our Global Reach',
            impact_communities: 'Communities Reached',
            impact_projects: 'Projects Completed',
            impact_lives: 'Lives Impacted',
            impact_transparency: '% Transparency',

            // About section
            about_title: 'Support in Action',
            about_text: 'Fajr.today is more than just a name; it\'s a commitment to clarity and renewal. Just as the dawn brings light to the world, we bring resources and resilience to those forgotten. Inspired by professional standards of global aid, we ensure every donation counts.',
            about_cta: 'Read Our Story',

            // Campaigns section
            campaigns_title: 'Ways to Support Fajr',
            campaign_monthly_title: 'Monthly Giving',
            campaign_monthly_desc: 'Provide reliable, ongoing support to our communities through automatic monthly contributions.',
            campaign_monthly_cta: 'GIVE MONTHLY',
            campaign_once_title: 'One-Time Gift',
            campaign_once_desc: 'Make an immediate impact with a single donation directed to our most urgent relief programs.',
            campaign_once_cta: 'GIVE ONCE',
            campaign_resilience_title: 'Resilience Fund',
            campaign_resilience_desc: 'Support long-term reconstruction and community strength through our dedicated resilience initiative.',
            campaign_resilience_cta: 'LEARN MORE',

            // Footer
            footer_rights: '© 2026 Fajr Today Group. All rights reserved.',

            // Toggle
            lang_toggle: 'عربي'
        },
        ar: {
            // Navigation
            nav_mission: 'مهمتنا',
            nav_impact: 'الأثر',
            nav_campaigns: 'الحملات',
            nav_contact: 'تواصل معنا',
            nav_donate: 'تبرع الآن',

            // Hero
            hero_title: 'نهاية الليل<br>بداية العمل',
            hero_subtitle: 'الفجر يرمز إلى لحظة الوضوح الدقيقة قبل الفجر. مع انتهاء الليل، تبدأ مهمتنا. متجذرون في صمود شجرة الزيتون، نجلب القوة والنور لمجتمعاتنا.',
            hero_cta: 'ادعم مهمتنا',
            hero_secondary: 'الرمزية',

            // Alert bar
            alert_matching: 'عاجل: جميع التبرعات يتم مضاعفتها حالياً — ضاعف أثرك اليوم',

            // Impact section
            impact_title: 'انتشارنا العالمي',
            impact_communities: 'مجتمع تم الوصول إليه',
            impact_projects: 'مشروع مكتمل',
            impact_lives: 'حياة تأثرت',
            impact_transparency: '% شفافية',

            // About section
            about_title: 'الدعم في العمل',
            about_text: 'فجر.اليوم أكثر من مجرد اسم؛ إنه التزام بالوضوح والتجديد. كما يجلب الفجر النور للعالم، نجلب الموارد والصمود لمن نُسيوا. مستوحاة من المعايير المهنية للمساعدات العالمية، نضمن أن كل تبرع يُحسب.',
            about_cta: 'اقرأ قصتنا',

            // Campaigns section
            campaigns_title: 'طرق دعم الفجر',
            campaign_monthly_title: 'العطاء الشهري',
            campaign_monthly_desc: 'قدم دعماً موثوقاً ومستمراً لمجتمعاتنا من خلال المساهمات الشهرية التلقائية.',
            campaign_monthly_cta: 'تبرع شهرياً',
            campaign_once_title: 'تبرع لمرة واحدة',
            campaign_once_desc: 'أحدث أثراً فورياً بتبرع واحد موجه لبرامج الإغاثة الأكثر إلحاحاً.',
            campaign_once_cta: 'تبرع مرة',
            campaign_resilience_title: 'صندوق الصمود',
            campaign_resilience_desc: 'ادعم إعادة البناء طويلة المدى وقوة المجتمع من خلال مبادرة الصمود المخصصة.',
            campaign_resilience_cta: 'اعرف المزيد',

            // Footer
            footer_rights: '© 2026 مجموعة فجر اليوم. جميع الحقوق محفوظة.',

            // Toggle
            lang_toggle: 'English'
        }
    },

    t(key) {
        return this.translations[this.currentLang][key] || key;
    },

    setLang(lang) {
        this.currentLang = lang;
        localStorage.setItem('lang', lang);
        document.documentElement.lang = lang;
        document.documentElement.dir = lang === 'ar' ? 'rtl' : 'ltr';
        this.updatePage();
    },

    toggle() {
        this.setLang(this.currentLang === 'en' ? 'ar' : 'en');
    },

    updatePage() {
        // Update all elements with data-i18n attribute
        document.querySelectorAll('[data-i18n]').forEach(el => {
            const key = el.getAttribute('data-i18n');
            el.innerHTML = this.t(key);
        });

        // Update toggle button text
        const toggleBtn = document.getElementById('lang-toggle');
        if (toggleBtn) {
            toggleBtn.textContent = this.t('lang_toggle');
        }
    },

    init() {
        document.documentElement.lang = this.currentLang;
        document.documentElement.dir = this.currentLang === 'ar' ? 'rtl' : 'ltr';
        this.updatePage();
    }
};

// Initialize on DOM load
window.addEventListener('DOMContentLoaded', () => {
    i18n.init();
});
