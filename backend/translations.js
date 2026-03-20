// translations.js
const translations = {
    ru: {
        // Общие
        app_name: "Need for Party",
        loading: "Загрузка...",
        guest: "Гость",
        not_authorized: "Не авторизован",
        menu: "Меню",
        slogan: "Тусовки твоей мечты",
        close: "Закрыть",
        
        // Навигация
        home: "Главная",
        verification: "Верификация",
        parties: "Вечеринки",
        discounts: "Скидки",
        roles: "Роли",
        gallery: "Галерея",
        tickets: "Мои билеты",
        support: "Поддержка",
        logout: "Выйти",
        
        // Регистрация/вход
        register_title: "Регистрация",
        login_title: "Вход",
        new_member: "Новый участник",
        existing_member: "Уже с нами",
        create_account: "Создать аккаунт",
        fill_data: "Заполните данные",
        name: "Имя",
        surname: "Фамилия",
        email: "Email",
        nickname: "Никнейм",
        password: "Пароль",
        confirm_password: "Подтвердите",
        email_example: "Например: ivan@mail.ru",
        nickname_min: "Минимум 3 символа",
        gender: "Ваш пол",
        male: "Мужской",
        female: "Женский",
        referral_code: "Реферальный код (если есть)",
        create_account_btn: "СОЗДАТЬ АККАУНТ",
        already_have_account: "Уже есть аккаунт?",
        login_link: "Войти",
        welcome_back: "Добро пожаловать!",
        login_btn: "ВОЙТИ В АККАУНТ",
        no_account: "Нет аккаунта?",
        register_link: "Зарегистрироваться",
        
        // Статистика
        my_stats: "📊 Моя статистика",
        visits: "Посещений",
        invited: "Приглашено",
        invite_friends: "👥 Пригласи друзей",
        your_referral_code: "Твой реферальный код:",
        copy_code: "Скопировать код",
        
        // QR
        my_qr: "📱 Мой QR-код",
        qr_description: "Покажи этот код на входе для быстрой проверки",
        scan_qr: "Сканировать QR-код",
        point_camera: "Наведите камеру на QR-код",
        download_qr: "Скачать QR",
        show_qr_info: "Покажите этот QR-код на входе",
        ticket_qr: "QR-код билета",
        
        // Роли
        my_roles: "🏆 Мои роли и прогресс",
        current_status: "Текущий статус",
        your_roles: "Ваши роли",
        loading_roles: "Загрузка ролей...",
        no_roles: "У вас пока нет ролей",
        path_to_legend: "Путь к Легенде",
        progress: "Прогресс:",
        roles_lower: "ролей",
        refresh: "Обновить",
        check_roles: "Проверить роли",
        
        // Названия ролей
        role_participant: "Участник",
        role_risky: "Рисковый",
        role_soul: "Душа компании",
        role_joker: "Весельчак",
        role_partier: "Тусовщик",
        role_ace: "Ас тусовок",
        role_legend: "Легенда",
        role_dancer: "Танцор",
        role_dancefloor: "Ас танцпола",
        role_drinker: "Любитель выпить",
        role_bar: "Глава бара",
        
        // Описания ролей
        role_participant_desc: "Новый участник системы",
        role_risky_desc: "Верифицированный пользователь",
        role_soul_desc: "Пригласил 5+ друзей",
        role_joker_desc: "Посетил 3+ вечеринки",
        role_partier_desc: "Посетил 5+ вечеринок",
        role_ace_desc: "Посетил 10+ вечеринок",
        role_legend_desc: "Получил все роли",
        role_dancer_desc: "Активный участник танцевальных батлов",
        role_dancefloor_desc: "Мастер танцпола",
        role_drinker_desc: "Ценитель напитков",
        role_bar_desc: "Великий покровитель бара",
        
        // Прогресс Легенды
        legend_achieved: "ЛЕГЕНДА ДОСТИГНУТА!",
        you_are_legend: "ВЫ ЛЕГЕНДА!",
        
        // Подтверждение выбора роли
        confirm_role_selection: 'Выбрать "{role}" в качестве основной роли?\n\nЭта роль будет отображаться в вашем профиле.',
        
        // Билеты
        my_tickets: "Мои билеты",
        no_tickets: "У вас нет билетов",
        buy_first_ticket: "Купите свой первый билет в разделе",
        ticket_for: "Билет на",
        active: "Активен",
        used: "Использован",
        show_qr: "Показать QR-код",
        
        // Вечеринки
        upcoming_parties: "Ближайшие вечеринки",
        buy_ticket: "Купить билет",
        sold_out: "Распродано",
        
        // Покупка билета
        buy_ticket_title: "🎫 Покупка билета",
        ticket_form: "Здесь будет форма покупки билета.",
        development: "⚠️ Функционал покупки в разработке",
        
        // Ошибки и уведомления
        error: "Ошибка",
        success: "Успешно",
        fill_all_fields: "Заполните все поля!",
        invalid_email: "Введите корректный email",
        password_length: "Пароль должен быть от 5 до 72 символов",
        passwords_dont_match: "Пароли не совпадают",
        choose_gender: "Выберите ваш пол",
        registration_success: "🎉 Регистрация успешна!",
        
        // Бан
        account_banned: "АККАУНТ ЗАБЛОКИРОВАН",
        banned_reason: "Ваш аккаунт был заблокирован",
        contact_support: "Свяжитесь с поддержкой",
        
        // Верификация
        verification_title: "🔐 Верификация личности",
        security_info: "Ваши данные в безопасности:",
        security_encryption: "✅ Все данные шифруются",
        security_metadata: "✅ Метаданные фото полностью удаляются",
        security_access: "✅ Доступ только у администраторов",
        citizenship: "Гражданство",
        choose_citizenship: "Выберите ваше гражданство",
        phone_number: "Номер телефона",
        phone_format: "Формат: 923 777 77 77 (10 цифр после +7)",
        document_id: "ID документа",
        document_placeholder: "Серия и номер паспорта / ID",
        document_only_digits: "Только цифры, максимум 20 символов",
        document_photo: "Фото документа",
        upload_photo: "Выбрать фото",
        take_photo: "Сделать фото",
        photo_formats: "JPG, PNG, GIF, BMP, TIFF, WEBP, HEIC (до 10MB)",
        submit_verification: "Отправить на проверку",
        document_pending: "⏳ Документ на проверке",
        pending_info: "Обычно проверка занимает до 24 часов",
        pending_notification: "Мы уведомим вас, когда верификация будет пройдена",
        verified: "ВЕРИФИКАЦИЯ ПРОЙДЕНА!",
        verified_message: "ваш аккаунт подтвержден",
        verified_benefits: "Ваши преимущества:",
        verified_discount: "Постоянная скидка +2% на все вечеринки"
    },
    
    en: {
        // General
        app_name: "Need for Party",
        loading: "Loading...",
        guest: "Guest",
        not_authorized: "Not authorized",
        menu: "Menu",
        slogan: "Parties of your dreams",
        close: "Close",
        
        // Navigation
        home: "Home",
        verification: "Verification",
        parties: "Parties",
        discounts: "Discounts",
        roles: "Roles",
        gallery: "Gallery",
        tickets: "My Tickets",
        support: "Support",
        logout: "Logout",
        
        // Registration/Login
        register_title: "Register",
        login_title: "Login",
        new_member: "New member",
        existing_member: "Already with us",
        create_account: "Create account",
        fill_data: "Fill the data",
        name: "Name",
        surname: "Surname",
        email: "Email",
        nickname: "Nickname",
        password: "Password",
        confirm_password: "Confirm",
        email_example: "Example: ivan@mail.ru",
        nickname_min: "Minimum 3 characters",
        gender: "Gender",
        male: "Male",
        female: "Female",
        referral_code: "Referral code (optional)",
        create_account_btn: "CREATE ACCOUNT",
        already_have_account: "Already have account?",
        login_link: "Login",
        welcome_back: "Welcome back!",
        login_btn: "LOGIN",
        no_account: "No account?",
        register_link: "Register",
        
        // Statistics
        my_stats: "📊 My Stats",
        visits: "Visits",
        invited: "Invited",
        invite_friends: "👥 Invite Friends",
        your_referral_code: "Your referral code:",
        copy_code: "Copy code",
        
        // QR
        my_qr: "📱 My QR Code",
        qr_description: "Show this code at the entrance for quick check",
        scan_qr: "Scan QR code",
        point_camera: "Point camera at QR code",
        download_qr: "Download QR",
        show_qr_info: "Show this QR code at the entrance",
        ticket_qr: "Ticket QR code",
        
        // Roles
        my_roles: "🏆 My Roles & Progress",
        current_status: "Current Status",
        your_roles: "Your Roles",
        loading_roles: "Loading roles...",
        no_roles: "You have no roles yet",
        path_to_legend: "Path to Legend",
        progress: "Progress:",
        roles_lower: "roles",
        refresh: "Refresh",
        check_roles: "Check roles",
        
        // Role names
        role_participant: "Participant",
        role_risky: "Risky",
        role_soul: "Life of the Party",
        role_joker: "Joker",
        role_partier: "Partier",
        role_ace: "Party Ace",
        role_legend: "Legend",
        role_dancer: "Dancer",
        role_dancefloor: "Dancefloor Ace",
        role_drinker: "Drink Lover",
        role_bar: "Bar Chief",
        
        // Role descriptions
        role_participant_desc: "New system participant",
        role_risky_desc: "Verified user",
        role_soul_desc: "Invited 5+ friends",
        role_joker_desc: "Visited 3+ parties",
        role_partier_desc: "Visited 5+ parties",
        role_ace_desc: "Visited 10+ parties",
        role_legend_desc: "Got all roles",
        role_dancer_desc: "Active dance battle participant",
        role_dancefloor_desc: "Dancefloor master",
        role_drinker_desc: "Drink connoisseur",
        role_bar_desc: "Great bar patron",
        
        // Legend progress
        legend_achieved: "LEGEND ACHIEVED!",
        you_are_legend: "YOU ARE LEGEND!",
        
        // Role selection confirmation
        confirm_role_selection: 'Choose "{role}" as your main role?\n\nThis role will be displayed in your profile.',
        
        // Tickets
        my_tickets: "My Tickets",
        no_tickets: "You have no tickets",
        buy_first_ticket: "Buy your first ticket in",
        ticket_for: "Ticket for",
        active: "Active",
        used: "Used",
        show_qr: "Show QR code",
        
        // Parties
        upcoming_parties: "Upcoming parties",
        buy_ticket: "Buy ticket",
        sold_out: "Sold out",
        
        // Ticket purchase
        buy_ticket_title: "🎫 Buy Ticket",
        ticket_form: "Ticket purchase form will be here.",
        development: "⚠️ Purchase functionality is under development",
        
        // Errors and notifications
        error: "Error",
        success: "Success",
        fill_all_fields: "Fill all fields!",
        invalid_email: "Enter valid email",
        password_length: "Password must be 5-72 characters",
        passwords_dont_match: "Passwords don't match",
        choose_gender: "Choose your gender",
        registration_success: "🎉 Registration successful!",
        
        // Ban
        account_banned: "ACCOUNT BANNED",
        banned_reason: "Your account has been banned",
        contact_support: "Contact support",
        
        // Verification
        verification_title: "🔐 Identity Verification",
        security_info: "Your data is secure:",
        security_encryption: "✅ All data is encrypted",
        security_metadata: "✅ Photo metadata is completely removed",
        security_access: "✅ Accessible only to administrators",
        citizenship: "Citizenship",
        choose_citizenship: "Choose your citizenship",
        phone_number: "Phone number",
        phone_format: "Format: 923 777 77 77 (10 digits after +7)",
        document_id: "Document ID",
        document_placeholder: "Passport series and number / ID",
        document_only_digits: "Digits only, maximum 20 characters",
        document_photo: "Document photo",
        upload_photo: "Choose photo",
        take_photo: "Take photo",
        photo_formats: "JPG, PNG, GIF, BMP, TIFF, WEBP, HEIC (up to 10MB)",
        submit_verification: "Submit for verification",
        document_pending: "⏳ Document under review",
        pending_info: "Verification usually takes up to 24 hours",
        pending_notification: "We will notify you when verification is complete",
        verified: "VERIFICATION COMPLETE!",
        verified_message: "your account has been verified",
        verified_benefits: "Your benefits:",
        verified_discount: "Permanent +2% discount on all parties"
    }
};

let currentLanguage = 'ru';

function t(key) {
    return translations[currentLanguage][key] || key;
}

function toggleLanguage() {
    currentLanguage = currentLanguage === 'ru' ? 'en' : 'ru';
    document.documentElement.lang = currentLanguage;
    updateUILanguage();
    localStorage.setItem('nfp_language', currentLanguage);
}

function updateUILanguage() {
    // Обновляем все тексты на странице
    document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.getAttribute('data-i18n');
        el.textContent = t(key);
    });
    
    // Обновляем плейсхолдеры
    document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
        const key = el.getAttribute('data-i18n-placeholder');
        el.placeholder = t(key);
    });
}

// Загружаем сохраненный язык
const savedLang = localStorage.getItem('nfp_language');
if (savedLang) {
    currentLanguage = savedLang;
}