// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for Arabic (`ar`).
class AppLocalizationsAr extends AppLocalizations {
  AppLocalizationsAr([String locale = 'ar']) : super(locale);

  @override
  String get navExplore => 'استكشاف';

  @override
  String get navBookings => 'الحجوزات';

  @override
  String get navCredits => 'رصيدي';

  @override
  String get navProfile => 'الإعدادات';

  @override
  String get retry => 'إعادة المحاولة';

  @override
  String get unexpectedError => 'حدث خطأ غير متوقع.';

  @override
  String get comingSoon => 'قريبًا';

  @override
  String get understood => 'حسنًا';

  @override
  String get loading => 'جارٍ التحميل';

  @override
  String get back => 'رجوع';

  @override
  String get chooseCity => 'اختر مدينة';

  @override
  String get nearYou => 'احجز بالقرب منك';

  @override
  String get seeAll => 'عرض الكل';

  @override
  String get seeOnMap => 'عرض على الخريطة';

  @override
  String get homeSearchHint => 'يوغا، حفلة، سبا، متحف…';

  @override
  String get todayChip => 'اليوم';

  @override
  String get tomorrowChip => 'غدًا';

  @override
  String get allUniverses => 'الكل';

  @override
  String get noSlotsThatDay =>
      'لا مواعيد في هذا التاريخ. جرّب يومًا أو عالمًا آخر.';

  @override
  String get welcomeTitle => 'اشتراك واحد، كل رغباتك';

  @override
  String get welcomeSubtitle =>
      'رياضة وثقافة وجمال وخروج — احجز بالأرصدة بالقرب منك.';

  @override
  String get signIn => 'تسجيل الدخول';

  @override
  String get signInHint => 'سجّل الدخول للحجز بأرصدتك في كل العوالم.';

  @override
  String get or => 'أو';

  @override
  String get createAccount => 'إنشاء حساب';

  @override
  String get passwordNotice =>
      'تُدخل كلمة المرور في صفحة XPASS الآمنة: التطبيق لا يراها أبدًا.';

  @override
  String get exploreWithoutAccount => 'الاستكشاف بدون حساب';

  @override
  String get demoMode => 'وضع العرض التجريبي';

  @override
  String get legalPending =>
      'الشروط العامة وسياسة الخصوصية: المستندات قيد الإعداد.';

  @override
  String get myProfile => 'الإعدادات';

  @override
  String get profileSubtitle => 'الحساب والتفضيلات والإشعارات والخصوصية.';

  @override
  String get emailVerified => 'تم التحقق من البريد الإلكتروني';

  @override
  String get emailNotVerified => 'حساب تجريبي (البريد الإلكتروني غير موثّق)';

  @override
  String get account => 'الحساب';

  @override
  String get personalInfo => 'المعلومات الشخصية';

  @override
  String get country => 'البلد';

  @override
  String get france => 'فرنسا';

  @override
  String get mySubscription => 'اشتراكي';

  @override
  String get preferences => 'التفضيلات';

  @override
  String get language => 'اللغة';

  @override
  String get bookingEmails => 'رسائل الحجز الإلكترونية';

  @override
  String get bookingEmailsHint => 'التأكيدات والإلغاءات والإيصالات';

  @override
  String get support => 'المساعدة';

  @override
  String get helpCenter => 'مركز المساعدة';

  @override
  String get contactSupport => 'التواصل مع الدعم';

  @override
  String get myRequests => 'طلباتي';

  @override
  String get privacy => 'الخصوصية';

  @override
  String get locationPermission => 'إذن الموقع';

  @override
  String get cameraPermission => 'إذن الكاميرا';

  @override
  String get optional => 'اختياري';

  @override
  String get exportData => 'تصدير بياناتي';

  @override
  String get deleteAccount => 'حذف حسابي';

  @override
  String get permissionsNotice =>
      'الموقع والكاميرا اختياريان: لا يُطلبان إلا عند استخدامهما (خريطة «بالقرب مني»)، ويمكنك رفضهما من إعدادات هاتفك.';

  @override
  String get signOut => 'تسجيل الخروج';

  @override
  String get translationNotice => 'يبقى محتوى المؤسسات بلغته الأصلية.';

  @override
  String get nearbyTitle => 'بالقرب مني';

  @override
  String get nearbySubtitle => 'اعثر على تجارب بالقرب منك';

  @override
  String get myPosition => 'موقعي';

  @override
  String get locateMe => 'حدّد موقعي';

  @override
  String get locating => 'جارٍ تحديد الموقع…';

  @override
  String get category => 'الفئة';

  @override
  String get allCategories => 'الكل';

  @override
  String get budget => 'الميزانية';

  @override
  String get anyBudget => 'الكل';

  @override
  String upToCredits(int count) {
    return '≤ $count رصيد';
  }

  @override
  String get searchThisArea => 'البحث في هذه المنطقة';

  @override
  String get noResultsArea =>
      'لا توجد تجارب في هذه المنطقة: وسّع النطاق أو غيّر عوامل التصفية.';

  @override
  String get loadPlacesError => 'تعذّر تحميل الأماكن.';

  @override
  String placesInRadius(int count, int km) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count أماكن',
      one: 'مكان واحد',
    );
    return '$_temp0 ضمن $km كم. المس السعر لعرض التفاصيل.';
  }

  @override
  String get directions => 'الاتجاهات';

  @override
  String get seeDetails => 'عرض التفاصيل';

  @override
  String get locationDisabled => 'خدمة الموقع متوقفة على هذا الجهاز.';

  @override
  String get locationDenied =>
      'تم رفض الموقع: تبقى الخريطة متمركزة على المدينة.';

  @override
  String get myBookings => 'حجوزاتي';

  @override
  String get myBookingsSubtitle => 'كل تجاربك في مكان واحد.';

  @override
  String get myCredits => 'رصيدي';

  @override
  String get signInToSeeBookings => 'سجّل الدخول لعرض حجوزاتك.';

  @override
  String get signInToSeeCredits => 'سجّل الدخول لعرض رصيدك.';

  @override
  String distanceAway(String distance) {
    return 'على بعد $distance';
  }

  @override
  String creditsCount(int count) {
    return '$count رصيد';
  }

  @override
  String radiusKm(int km) {
    return '$km كيلومتر';
  }

  @override
  String get filterDate => 'التاريخ';

  @override
  String get filterParticipants => 'المشاركون';

  @override
  String nextSlotAt(String when) {
    return 'الموعد القادم: $when';
  }

  @override
  String get dateFilterSoon =>
      'التصفية حسب التاريخ قريبًا: تعرض الخريطة الأماكن، ويُختار الموعد من صفحة المكان.';

  @override
  String get participantsFilterSoon =>
      'التصفية حسب عدد المشاركين قريبًا: يُحدَّد العدد عند الحجز.';

  @override
  String get recenter => 'إعادة توسيط الخريطة';

  @override
  String get creditsUnit => 'رصيد';

  @override
  String get soonShort => 'قريبًا';

  @override
  String get myFavorites => 'مفضلاتي';

  @override
  String participantsCount(int count) {
    return '$count أشخاص';
  }

  @override
  String get anyDate => 'أي وقت';

  @override
  String get anyParticipants => 'الكل';

  @override
  String get openThatDay => 'مفتوح في ذلك اليوم';

  @override
  String get settings => 'الإعدادات';

  @override
  String get mySpace => 'مساحتي';

  @override
  String get help => 'المساعدة';

  @override
  String get emailAddress => 'البريد الإلكتروني';

  @override
  String get passwordSecurity => 'كلمة المرور والأمان';

  @override
  String get notifications => 'الإشعارات';

  @override
  String get pushNotifications => 'إشعارات الهاتف';

  @override
  String get legalDocs => 'الشروط والخصوصية';

  @override
  String get inDrafting => 'قيد الإعداد';

  @override
  String get about => 'حول التطبيق';

  @override
  String get appVersion => 'إصدار التطبيق';

  @override
  String get dangerZone => 'منطقة حساسة';

  @override
  String get settingsSubtitle => 'الحساب والتفضيلات والإشعارات والخصوصية.';

  @override
  String get noOffersYet => 'لا يقدم هذا المكان أي تجربة حاليًا.';

  @override
  String get externalTicket => 'تذكرة خارجية';

  @override
  String get externalTicketIssued => 'يصدر التذكرة الموزّع الشريك.';

  @override
  String get nextOpeningSlot => 'أقرب موعد متاح';

  @override
  String get accordingToHours =>
      'حسب ساعات العمل. تظهر الأماكن المتبقية في التقويم.';

  @override
  String get noSlot14Days => 'لا توجد مواعيد خلال 14 يومًا القادمة';

  @override
  String get ticketAtDistributor => 'التذكرة لدى الموزّع';

  @override
  String get externalTicketNoSlot =>
      'تصدر هذه التذكرة من الموزّع الشريك: لا تُحجز بموعد XPASS.';

  @override
  String get seeCalendar => 'عرض التقويم';

  @override
  String get wheelchairAccessible => 'مهيأ لذوي الحركة المحدودة';

  @override
  String get accessibilityNotGuaranteed => 'إمكانية الوصول غير مضمونة';

  @override
  String get chooseMySlot => 'اختر موعدي';

  @override
  String get availableTimes => 'الأوقات المتاحة';

  @override
  String get noTimeThatDay =>
      'لا توجد أوقات متاحة في هذا اليوم. جرّب تاريخًا آخر.';

  @override
  String get holdingSlot => 'جارٍ حجز الموعد…';

  @override
  String get noPreference => 'بدون تفضيل';

  @override
  String get removeParticipant => 'إزالة مشارك';

  @override
  String get addParticipant => 'إضافة مشارك';

  @override
  String get confirmBooking => 'تأكيد الحجز';

  @override
  String get checkBeforeConfirm => 'تحقق من تفاصيل حجزك قبل التأكيد.';

  @override
  String get timeExpired => 'انتهت المهلة';

  @override
  String get slotReleased =>
      'تم تحرير الموعد وإرجاع رصيدك. اختر موعدًا جديدًا.';

  @override
  String get chooseAnotherSlot => 'اختر موعدًا آخر';

  @override
  String get bookingConfirmed => 'تم تأكيد الحجز';

  @override
  String get creditsHeld => 'رصيدك محجوز ولم يُستخدم بعد.';

  @override
  String get freeCancelUntil => 'يمكنك الإلغاء مجانًا حتى هذا التاريخ.';

  @override
  String get cancelAfterDate => 'في حال الإلغاء بعد هذا التاريخ';

  @override
  String get sessionConfirmed => 'تم تأكيد موعدك. إلى اللقاء قريبًا!';

  @override
  String get addToCalendar => 'أضف إلى تقويمي';

  @override
  String get writeToVenue => 'راسل المكان';

  @override
  String get cancelBooking => 'إلغاء الحجز';

  @override
  String get needHelp => 'تحتاج مساعدة؟';

  @override
  String get cancelBookingQuestion => 'إلغاء الحجز؟';

  @override
  String get cancelledCharged => 'تم إلغاء الحجز وخصم الرصيد.';

  @override
  String get cancelledRefunded => 'تم إلغاء الحجز وإرجاع الرصيد.';

  @override
  String get qrSemantics => 'رمز QR للحجز لتقديمه للشريك';

  @override
  String get showToPartner => 'قدّمه للشريك';

  @override
  String get calendarIntro => 'اعثر على تفاصيل حجزك في التقويم الذي تختاره.';

  @override
  String get chooseCalendar => 'اختر تقويمًا';

  @override
  String get phoneCalendar => 'تقويم الهاتف (ملف ‎.ics)';

  @override
  String get reminderSuggested => 'تذكير مقترح: قبل ساعة (مضمّن في ملف ‎.ics)';

  @override
  String get calendarNoQr =>
      'يحتوي الحدث على الوقت والعنوان وليس رمز QR: قدّمه من التطبيق.';

  @override
  String get serviceDoneTitle => 'انتهت تجربتك!';

  @override
  String get thanksBenefit => 'شكرًا لاستفادتك من ميزتك مع XPASS.';

  @override
  String get serviceDone => 'تمت الخدمة';

  @override
  String get validatedByPartner => 'صادق عليها الشريك.';

  @override
  String get creditsUsed => 'الرصيد المستخدم';

  @override
  String get receiptReference => 'مرجع الإيصال';

  @override
  String get reviewOnGoogle => 'اكتب رأيك على Google';

  @override
  String get reviewFree => 'رأيك حر واختياري.';

  @override
  String get noReviewLink => 'لم يضف هذا المكان رابط تقييم بعد.';

  @override
  String get askForHelp => 'اطلب المساعدة';

  @override
  String get slotPricePeak => 'وقت الذروة';

  @override
  String get slotPriceDemand => 'طلب مرتفع';

  @override
  String get slotPriceLastMinute => 'اللحظة الأخيرة';

  @override
  String get slotPriceLegend =>
      'يتغير السعر حسب الوقت والطلب: ↑ وقت الذروة أو طلب مرتفع، ↓ اللحظة الأخيرة.';

  @override
  String lateCancelInfo(String refund, String total) {
    return 'بعد هذا الموعد، يعيد الإلغاء $refund من أصل $total (النصف). بدون إلغاء ولا حضور، يُستهلك كل شيء.';
  }

  @override
  String cancelledPartlyRefunded(String refund) {
    return 'تم إلغاء الحجز: أُعيد إليك $refund.';
  }

  @override
  String get creditRulesTitle => 'كيف تعمل أرصدتك';

  @override
  String get creditRulePrice =>
      'يتغير سعر الموعد: أغلى في أوقات الذروة (↑) وأرخص في اللحظة الأخيرة (↓). يُثبَّت السعر عند الحجز.';

  @override
  String get creditRuleCancel =>
      'الإلغاء مجاني حتى الموعد المحدد؛ بعده يُعاد إليك نصف الأرصدة. بدون إلغاء ولا حضور، يُستهلك كل شيء.';

  @override
  String get creditRuleRollover =>
      'أرصدة الاشتراك غير المستخدمة تُرحَّل إلى الشهر التالي في حدود شهر من باقتك، وتنتهي عند إيقاف الاشتراك.';

  @override
  String get creditRuleEmployer =>
      'الأرصدة المقدمة من صاحب العمل تُستخدم أولاً، ضمن مدة الصلاحية التي تحددها الشركة.';

  @override
  String get madeByAlystra => 'من تطوير Alystra';

  @override
  String get pushNotificationsHint => 'تنبيهات الحجوزات والمدفوعات والرسائل';

  @override
  String get noNotifications => 'لا توجد إشعارات حالياً.';

  @override
  String get notificationsSubtitle => 'الحجوزات والمدفوعات وردود الفريق.';
}
