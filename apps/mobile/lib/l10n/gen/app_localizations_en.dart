// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for English (`en`).
class AppLocalizationsEn extends AppLocalizations {
  AppLocalizationsEn([String locale = 'en']) : super(locale);

  @override
  String get navExplore => 'Explore';

  @override
  String get navBookings => 'Bookings';

  @override
  String get navCredits => 'My credits';

  @override
  String get navProfile => 'Settings';

  @override
  String get retry => 'Try again';

  @override
  String get unexpectedError => 'An unexpected error occurred.';

  @override
  String get comingSoon => 'Coming soon';

  @override
  String get understood => 'Got it';

  @override
  String get loading => 'Loading';

  @override
  String get back => 'Back';

  @override
  String get chooseCity => 'Choose a city';

  @override
  String get nearYou => 'Book near you';

  @override
  String get seeAll => 'See all';

  @override
  String get seeOnMap => 'See on the map';

  @override
  String get homeSearchHint => 'Yoga, concert, spa, museum…';

  @override
  String get todayChip => 'Today';

  @override
  String get tomorrowChip => 'Tomorrow';

  @override
  String get allUniverses => 'All';

  @override
  String get noSlotsThatDay =>
      'No slots on this date. Try another day or universe.';

  @override
  String get welcomeTitle => 'One pass, every craving';

  @override
  String get welcomeSubtitle =>
      'Sport, culture, beauty and nights out — book with credits, near you.';

  @override
  String get signIn => 'Sign in';

  @override
  String get signInHint =>
      'Sign in to book with your credits, across every universe.';

  @override
  String get or => 'or';

  @override
  String get createAccount => 'Create an account';

  @override
  String get passwordNotice =>
      'You enter your password on the secure XPASS page: the app never sees it.';

  @override
  String get exploreWithoutAccount => 'Explore without an account';

  @override
  String get demoMode => 'Demo mode';

  @override
  String get legalPending =>
      'Terms of use and privacy policy: documents being drafted.';

  @override
  String get myProfile => 'Settings';

  @override
  String get profileSubtitle =>
      'Account, preferences, notifications and privacy.';

  @override
  String get emailVerified => 'Email address verified';

  @override
  String get emailNotVerified => 'Demo account (email not verified)';

  @override
  String get account => 'Account';

  @override
  String get personalInfo => 'Personal information';

  @override
  String get country => 'Country';

  @override
  String get france => 'France';

  @override
  String get mySubscription => 'My subscription';

  @override
  String get preferences => 'Preferences';

  @override
  String get language => 'Language';

  @override
  String get bookingEmails => 'Booking emails';

  @override
  String get bookingEmailsHint => 'Confirmations, cancellations and receipts';

  @override
  String get support => 'Support';

  @override
  String get helpCenter => 'Help centre';

  @override
  String get contactSupport => 'Contact support';

  @override
  String get myRequests => 'My requests';

  @override
  String get privacy => 'Privacy';

  @override
  String get locationPermission => 'Location permission';

  @override
  String get cameraPermission => 'Camera permission';

  @override
  String get optional => 'Optional';

  @override
  String get exportData => 'Export my data';

  @override
  String get deleteAccount => 'Delete my account';

  @override
  String get permissionsNotice =>
      'Location and camera are optional: they are only requested when you use them (\"Near me\" map), and you can refuse them in your phone settings.';

  @override
  String get signOut => 'Sign out';

  @override
  String get translationNotice =>
      'Venue content stays in its original language.';

  @override
  String get nearbyTitle => 'Near me';

  @override
  String get nearbySubtitle => 'Find experiences close to you';

  @override
  String get myPosition => 'My location';

  @override
  String get locateMe => 'Locate me';

  @override
  String get locating => 'Locating…';

  @override
  String get category => 'Category';

  @override
  String get allCategories => 'All';

  @override
  String get budget => 'Budget';

  @override
  String get anyBudget => 'Any';

  @override
  String upToCredits(int count) {
    return '≤ $count credits';
  }

  @override
  String get searchThisArea => 'Search this area';

  @override
  String get noResultsArea =>
      'No experiences in this area: widen the radius or change the filters.';

  @override
  String get loadPlacesError => 'Unable to load places.';

  @override
  String placesInRadius(int count, int km) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count places',
      one: '1 place',
    );
    return '$_temp0 within $km km. Tap a price to see the details.';
  }

  @override
  String get directions => 'Directions';

  @override
  String get seeDetails => 'See details';

  @override
  String get locationDisabled => 'Location is turned off on this device.';

  @override
  String get locationDenied =>
      'Location denied: the map stays centred on the city.';

  @override
  String get myBookings => 'My bookings';

  @override
  String get myBookingsSubtitle => 'All your experiences in one place.';

  @override
  String get myCredits => 'My credits';

  @override
  String get signInToSeeBookings => 'Sign in to see your bookings.';

  @override
  String get signInToSeeCredits => 'Sign in to see your credits.';

  @override
  String distanceAway(String distance) {
    return '$distance away';
  }

  @override
  String creditsCount(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count credits',
      one: '1 credit',
    );
    return '$_temp0';
  }

  @override
  String radiusKm(int km) {
    return '$km kilometres';
  }

  @override
  String get filterDate => 'Date';

  @override
  String get filterParticipants => 'Participants';

  @override
  String nextSlotAt(String when) {
    return 'Next slot: $when';
  }

  @override
  String get dateFilterSoon =>
      'Filtering by date is coming soon: the map shows places, and you pick a slot on the place page.';

  @override
  String get participantsFilterSoon =>
      'Filtering by number of participants is coming soon: you choose it when booking.';

  @override
  String get recenter => 'Recentre the map';

  @override
  String get creditsUnit => 'credits';

  @override
  String get soonShort => 'Soon';

  @override
  String get myFavorites => 'My favourites';

  @override
  String participantsCount(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count people',
      one: '1 person',
    );
    return '$_temp0';
  }

  @override
  String get anyDate => 'Any time';

  @override
  String get anyParticipants => 'Any';

  @override
  String get openThatDay => 'Open that day';

  @override
  String get settings => 'Settings';

  @override
  String get mySpace => 'My space';

  @override
  String get help => 'Help';

  @override
  String get emailAddress => 'Email address';

  @override
  String get passwordSecurity => 'Password and security';

  @override
  String get notifications => 'Notifications';

  @override
  String get pushNotifications => 'Phone notifications';

  @override
  String get legalDocs => 'Terms and privacy';

  @override
  String get inDrafting => 'Being drafted';

  @override
  String get about => 'About';

  @override
  String get appVersion => 'App version';

  @override
  String get dangerZone => 'Danger zone';

  @override
  String get settingsSubtitle =>
      'Account, preferences, notifications and privacy.';

  @override
  String get noOffersYet => 'This venue has no experiences yet.';

  @override
  String get externalTicket => 'External ticket';

  @override
  String get externalTicketIssued =>
      'The ticket is issued by the partner distributor.';

  @override
  String get nextOpeningSlot => 'Next opening slot';

  @override
  String get accordingToHours =>
      'Based on opening hours. Remaining places are shown in the calendar.';

  @override
  String get noSlot14Days => 'No slot in the next 14 days';

  @override
  String get ticketAtDistributor => 'Ticket from the distributor';

  @override
  String get externalTicketNoSlot =>
      'This ticket is issued by the partner distributor: it is not booked with an XPASS slot.';

  @override
  String get seeCalendar => 'See the calendar';

  @override
  String get wheelchairAccessible => 'Wheelchair accessible';

  @override
  String get accessibilityNotGuaranteed => 'Accessibility not guaranteed';

  @override
  String get chooseMySlot => 'Choose my slot';

  @override
  String get availableTimes => 'Available times';

  @override
  String get noTimeThatDay => 'No time available that day. Try another date.';

  @override
  String get holdingSlot => 'Holding the slot…';

  @override
  String get noPreference => 'No preference';

  @override
  String get removeParticipant => 'Remove a participant';

  @override
  String get addParticipant => 'Add a participant';

  @override
  String get confirmBooking => 'Confirm the booking';

  @override
  String get checkBeforeConfirm =>
      'Check your booking details before confirming.';

  @override
  String get timeExpired => 'Time expired';

  @override
  String get slotReleased =>
      'The slot was released and your credits returned. Choose a new slot.';

  @override
  String get chooseAnotherSlot => 'Choose another slot';

  @override
  String get bookingConfirmed => 'Booking confirmed';

  @override
  String get creditsHeld => 'Your credits are held, not yet used.';

  @override
  String get freeCancelUntil =>
      'You can cancel free of charge until this date.';

  @override
  String get cancelAfterDate => 'If you cancel after this date';

  @override
  String get sessionConfirmed => 'Your session is confirmed. See you soon!';

  @override
  String get addToCalendar => 'Add to my calendar';

  @override
  String get writeToVenue => 'Message the venue';

  @override
  String get cancelBooking => 'Cancel the booking';

  @override
  String get needHelp => 'Need help?';

  @override
  String get cancelBookingQuestion => 'Cancel the booking?';

  @override
  String get cancelledCharged => 'Booking cancelled, credits charged.';

  @override
  String get cancelledRefunded => 'Booking cancelled, credits returned.';

  @override
  String get qrSemantics => 'Booking QR code to show to the partner';

  @override
  String get showToPartner => 'Show it to the partner';

  @override
  String get calendarIntro =>
      'Find your booking details in the calendar of your choice.';

  @override
  String get chooseCalendar => 'Choose a calendar';

  @override
  String get phoneCalendar => 'Phone calendar (.ics file)';

  @override
  String get reminderSuggested =>
      'Suggested reminder: 1 h before (included in the .ics file)';

  @override
  String get calendarNoQr =>
      'The event contains the time and address, never your QR: show it from the app.';

  @override
  String get serviceDoneTitle => 'Your experience is complete!';

  @override
  String get thanksBenefit => 'Thank you for enjoying your benefit with XPASS.';

  @override
  String get serviceDone => 'Experience completed';

  @override
  String get validatedByPartner => 'Validated by the partner.';

  @override
  String get creditsUsed => 'Credits used';

  @override
  String get receiptReference => 'Receipt reference';

  @override
  String get reviewOnGoogle => 'Leave a review on Google';

  @override
  String get reviewFree => 'Your review is free and optional.';

  @override
  String get noReviewLink => 'This venue has not added a review link yet.';

  @override
  String get askForHelp => 'Ask for help';

  @override
  String get slotPricePeak => 'Peak time';

  @override
  String get slotPriceDemand => 'High demand';

  @override
  String get slotPriceLastMinute => 'Last minute';

  @override
  String get slotPriceLegend =>
      'Prices vary with time and demand: ↑ peak time or high demand, ↓ last minute.';

  @override
  String lateCancelInfo(String refund, String total) {
    return 'After this time, cancelling gives back $refund out of $total (half). If you neither cancel nor show up, everything is used.';
  }

  @override
  String cancelledPartlyRefunded(String refund) {
    return 'Booking cancelled: $refund have been given back.';
  }

  @override
  String get creditRulesTitle => 'How your credits work';

  @override
  String get creditRulePrice =>
      'Slot prices vary: higher at peak times (↑), lower at the last minute (↓). The price is fixed when you book.';

  @override
  String get creditRuleCancel =>
      'Free cancellation until the stated time; after that, half of the credits are given back. If you neither cancel nor show up, everything is used.';

  @override
  String get creditRuleRollover =>
      'Unused subscription credits roll over to the next month, up to one month of your plan; they expire when the subscription ends.';

  @override
  String get creditRuleEmployer =>
      'Credits offered by your employer are used first, within the validity period set by your company.';

  @override
  String get madeByAlystra => 'Made by Alystra';

  @override
  String get pushNotificationsHint =>
      'Alerts for bookings, payments and messages';

  @override
  String get noNotifications => 'No notifications yet.';

  @override
  String get notificationsSubtitle =>
      'Bookings, payments and replies from the team.';
}
