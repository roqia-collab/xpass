import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:intl/intl.dart' as intl;

import 'app_localizations_ar.dart';
import 'app_localizations_en.dart';
import 'app_localizations_fr.dart';

// ignore_for_file: type=lint

/// Callers can lookup localized strings with an instance of AppLocalizations
/// returned by `AppLocalizations.of(context)`.
///
/// Applications need to include `AppLocalizations.delegate()` in their app's
/// `localizationDelegates` list, and the locales they support in the app's
/// `supportedLocales` list. For example:
///
/// ```dart
/// import 'gen/app_localizations.dart';
///
/// return MaterialApp(
///   localizationsDelegates: AppLocalizations.localizationsDelegates,
///   supportedLocales: AppLocalizations.supportedLocales,
///   home: MyApplicationHome(),
/// );
/// ```
///
/// ## Update pubspec.yaml
///
/// Please make sure to update your pubspec.yaml to include the following
/// packages:
///
/// ```yaml
/// dependencies:
///   # Internationalization support.
///   flutter_localizations:
///     sdk: flutter
///   intl: any # Use the pinned version from flutter_localizations
///
///   # Rest of dependencies
/// ```
///
/// ## iOS Applications
///
/// iOS applications define key application metadata, including supported
/// locales, in an Info.plist file that is built into the application bundle.
/// To configure the locales supported by your app, you’ll need to edit this
/// file.
///
/// First, open your project’s ios/Runner.xcworkspace Xcode workspace file.
/// Then, in the Project Navigator, open the Info.plist file under the Runner
/// project’s Runner folder.
///
/// Next, select the Information Property List item, select Add Item from the
/// Editor menu, then select Localizations from the pop-up menu.
///
/// Select and expand the newly-created Localizations item then, for each
/// locale your application supports, add a new item and select the locale
/// you wish to add from the pop-up menu in the Value field. This list should
/// be consistent with the languages listed in the AppLocalizations.supportedLocales
/// property.
abstract class AppLocalizations {
  AppLocalizations(String locale)
      : localeName = intl.Intl.canonicalizedLocale(locale.toString());

  final String localeName;

  static AppLocalizations of(BuildContext context) {
    return Localizations.of<AppLocalizations>(context, AppLocalizations)!;
  }

  static const LocalizationsDelegate<AppLocalizations> delegate =
      _AppLocalizationsDelegate();

  /// A list of this localizations delegate along with the default localizations
  /// delegates.
  ///
  /// Returns a list of localizations delegates containing this delegate along with
  /// GlobalMaterialLocalizations.delegate, GlobalCupertinoLocalizations.delegate,
  /// and GlobalWidgetsLocalizations.delegate.
  ///
  /// Additional delegates can be added by appending to this list in
  /// MaterialApp. This list does not have to be used at all if a custom list
  /// of delegates is preferred or required.
  static const List<LocalizationsDelegate<dynamic>> localizationsDelegates =
      <LocalizationsDelegate<dynamic>>[
    delegate,
    GlobalMaterialLocalizations.delegate,
    GlobalCupertinoLocalizations.delegate,
    GlobalWidgetsLocalizations.delegate,
  ];

  /// A list of this localizations delegate's supported locales.
  static const List<Locale> supportedLocales = <Locale>[
    Locale('ar'),
    Locale('en'),
    Locale('fr')
  ];

  /// No description provided for @navExplore.
  ///
  /// In fr, this message translates to:
  /// **'Explorer'**
  String get navExplore;

  /// No description provided for @navBookings.
  ///
  /// In fr, this message translates to:
  /// **'Réservations'**
  String get navBookings;

  /// No description provided for @navCredits.
  ///
  /// In fr, this message translates to:
  /// **'Mes crédits'**
  String get navCredits;

  /// No description provided for @navProfile.
  ///
  /// In fr, this message translates to:
  /// **'Paramètres'**
  String get navProfile;

  /// No description provided for @retry.
  ///
  /// In fr, this message translates to:
  /// **'Réessayer'**
  String get retry;

  /// No description provided for @unexpectedError.
  ///
  /// In fr, this message translates to:
  /// **'Une erreur inattendue est survenue.'**
  String get unexpectedError;

  /// No description provided for @comingSoon.
  ///
  /// In fr, this message translates to:
  /// **'Bientôt disponible'**
  String get comingSoon;

  /// No description provided for @understood.
  ///
  /// In fr, this message translates to:
  /// **'Compris'**
  String get understood;

  /// No description provided for @loading.
  ///
  /// In fr, this message translates to:
  /// **'Chargement'**
  String get loading;

  /// No description provided for @back.
  ///
  /// In fr, this message translates to:
  /// **'Retour'**
  String get back;

  /// No description provided for @chooseCity.
  ///
  /// In fr, this message translates to:
  /// **'Choisir une ville'**
  String get chooseCity;

  /// No description provided for @nearYou.
  ///
  /// In fr, this message translates to:
  /// **'À réserver près de vous'**
  String get nearYou;

  /// No description provided for @seeAll.
  ///
  /// In fr, this message translates to:
  /// **'Voir tout'**
  String get seeAll;

  /// No description provided for @seeOnMap.
  ///
  /// In fr, this message translates to:
  /// **'Voir sur la carte'**
  String get seeOnMap;

  /// No description provided for @homeSearchHint.
  ///
  /// In fr, this message translates to:
  /// **'Yoga, concert, spa, musée…'**
  String get homeSearchHint;

  /// No description provided for @todayChip.
  ///
  /// In fr, this message translates to:
  /// **'Aujourd\'hui'**
  String get todayChip;

  /// No description provided for @tomorrowChip.
  ///
  /// In fr, this message translates to:
  /// **'Demain'**
  String get tomorrowChip;

  /// No description provided for @allUniverses.
  ///
  /// In fr, this message translates to:
  /// **'Tout'**
  String get allUniverses;

  /// No description provided for @noSlotsThatDay.
  ///
  /// In fr, this message translates to:
  /// **'Aucun créneau à cette date. Changez de jour ou d’univers.'**
  String get noSlotsThatDay;

  /// No description provided for @welcomeTitle.
  ///
  /// In fr, this message translates to:
  /// **'Un pass, toutes vos envies'**
  String get welcomeTitle;

  /// No description provided for @welcomeSubtitle.
  ///
  /// In fr, this message translates to:
  /// **'Sport, culture, beauté et sorties — réservez avec des crédits, près de chez vous.'**
  String get welcomeSubtitle;

  /// No description provided for @signIn.
  ///
  /// In fr, this message translates to:
  /// **'Continuer avec Google'**
  String get signIn;

  /// No description provided for @signInHint.
  ///
  /// In fr, this message translates to:
  /// **'Connectez-vous pour réserver avec vos crédits, dans tous les univers.'**
  String get signInHint;

  /// No description provided for @or.
  ///
  /// In fr, this message translates to:
  /// **'ou'**
  String get or;

  /// No description provided for @createAccount.
  ///
  /// In fr, this message translates to:
  /// **'Créer un compte'**
  String get createAccount;

  /// No description provided for @passwordNotice.
  ///
  /// In fr, this message translates to:
  /// **'Connexion avec votre compte Google. L’application ne voit jamais votre mot de passe.'**
  String get passwordNotice;

  /// No description provided for @exploreWithoutAccount.
  ///
  /// In fr, this message translates to:
  /// **'Explorer sans compte'**
  String get exploreWithoutAccount;

  /// No description provided for @demoMode.
  ///
  /// In fr, this message translates to:
  /// **'Mode démonstration'**
  String get demoMode;

  /// No description provided for @legalPending.
  ///
  /// In fr, this message translates to:
  /// **'Conditions générales et politique de confidentialité : documents en cours de rédaction.'**
  String get legalPending;

  /// No description provided for @myProfile.
  ///
  /// In fr, this message translates to:
  /// **'Paramètres'**
  String get myProfile;

  /// No description provided for @profileSubtitle.
  ///
  /// In fr, this message translates to:
  /// **'Compte, préférences, notifications et confidentialité.'**
  String get profileSubtitle;

  /// No description provided for @emailVerified.
  ///
  /// In fr, this message translates to:
  /// **'Adresse e-mail vérifiée'**
  String get emailVerified;

  /// No description provided for @emailNotVerified.
  ///
  /// In fr, this message translates to:
  /// **'Compte de démonstration (e-mail non vérifié)'**
  String get emailNotVerified;

  /// No description provided for @account.
  ///
  /// In fr, this message translates to:
  /// **'Compte'**
  String get account;

  /// No description provided for @personalInfo.
  ///
  /// In fr, this message translates to:
  /// **'Informations personnelles'**
  String get personalInfo;

  /// No description provided for @country.
  ///
  /// In fr, this message translates to:
  /// **'Pays'**
  String get country;

  /// No description provided for @france.
  ///
  /// In fr, this message translates to:
  /// **'France'**
  String get france;

  /// No description provided for @mySubscription.
  ///
  /// In fr, this message translates to:
  /// **'Mon abonnement'**
  String get mySubscription;

  /// No description provided for @preferences.
  ///
  /// In fr, this message translates to:
  /// **'Préférences'**
  String get preferences;

  /// No description provided for @language.
  ///
  /// In fr, this message translates to:
  /// **'Langue'**
  String get language;

  /// No description provided for @bookingEmails.
  ///
  /// In fr, this message translates to:
  /// **'E-mails de réservation'**
  String get bookingEmails;

  /// No description provided for @bookingEmailsHint.
  ///
  /// In fr, this message translates to:
  /// **'Confirmations, annulations et reçus'**
  String get bookingEmailsHint;

  /// No description provided for @support.
  ///
  /// In fr, this message translates to:
  /// **'Assistance'**
  String get support;

  /// No description provided for @helpCenter.
  ///
  /// In fr, this message translates to:
  /// **'Centre d’aide'**
  String get helpCenter;

  /// No description provided for @contactSupport.
  ///
  /// In fr, this message translates to:
  /// **'Contacter le support'**
  String get contactSupport;

  /// No description provided for @myRequests.
  ///
  /// In fr, this message translates to:
  /// **'Mes demandes'**
  String get myRequests;

  /// No description provided for @privacy.
  ///
  /// In fr, this message translates to:
  /// **'Confidentialité'**
  String get privacy;

  /// No description provided for @locationPermission.
  ///
  /// In fr, this message translates to:
  /// **'Permissions localisation'**
  String get locationPermission;

  /// No description provided for @cameraPermission.
  ///
  /// In fr, this message translates to:
  /// **'Permissions caméra'**
  String get cameraPermission;

  /// No description provided for @optional.
  ///
  /// In fr, this message translates to:
  /// **'Optionnel'**
  String get optional;

  /// No description provided for @exportData.
  ///
  /// In fr, this message translates to:
  /// **'Exporter mes données'**
  String get exportData;

  /// No description provided for @deleteAccount.
  ///
  /// In fr, this message translates to:
  /// **'Supprimer mon compte'**
  String get deleteAccount;

  /// No description provided for @permissionsNotice.
  ///
  /// In fr, this message translates to:
  /// **'La localisation et la caméra sont optionnelles : elles ne sont demandées qu’au moment de les utiliser (carte « Autour de moi »), et vous pouvez les refuser dans les réglages de votre téléphone.'**
  String get permissionsNotice;

  /// No description provided for @signOut.
  ///
  /// In fr, this message translates to:
  /// **'Se déconnecter'**
  String get signOut;

  /// No description provided for @translationNotice.
  ///
  /// In fr, this message translates to:
  /// **'Les contenus des établissements restent dans leur langue d’origine.'**
  String get translationNotice;

  /// No description provided for @nearbyTitle.
  ///
  /// In fr, this message translates to:
  /// **'Autour de moi'**
  String get nearbyTitle;

  /// No description provided for @nearbySubtitle.
  ///
  /// In fr, this message translates to:
  /// **'Trouvez des expériences près de chez vous'**
  String get nearbySubtitle;

  /// No description provided for @myPosition.
  ///
  /// In fr, this message translates to:
  /// **'Ma position'**
  String get myPosition;

  /// No description provided for @locateMe.
  ///
  /// In fr, this message translates to:
  /// **'Me localiser'**
  String get locateMe;

  /// No description provided for @locating.
  ///
  /// In fr, this message translates to:
  /// **'Localisation…'**
  String get locating;

  /// No description provided for @category.
  ///
  /// In fr, this message translates to:
  /// **'Catégorie'**
  String get category;

  /// No description provided for @allCategories.
  ///
  /// In fr, this message translates to:
  /// **'Toutes'**
  String get allCategories;

  /// No description provided for @budget.
  ///
  /// In fr, this message translates to:
  /// **'Budget'**
  String get budget;

  /// No description provided for @anyBudget.
  ///
  /// In fr, this message translates to:
  /// **'Tous'**
  String get anyBudget;

  /// No description provided for @upToCredits.
  ///
  /// In fr, this message translates to:
  /// **'≤ {count} crédits'**
  String upToCredits(int count);

  /// No description provided for @searchThisArea.
  ///
  /// In fr, this message translates to:
  /// **'Rechercher dans cette zone'**
  String get searchThisArea;

  /// No description provided for @noResultsArea.
  ///
  /// In fr, this message translates to:
  /// **'Aucune expérience dans cette zone : élargissez le rayon ou changez les filtres.'**
  String get noResultsArea;

  /// No description provided for @loadPlacesError.
  ///
  /// In fr, this message translates to:
  /// **'Impossible de charger les lieux.'**
  String get loadPlacesError;

  /// No description provided for @placesInRadius.
  ///
  /// In fr, this message translates to:
  /// **'{count, plural, =1{1 lieu} other{{count} lieux}} dans un rayon de {km} km. Touchez un prix pour voir la fiche.'**
  String placesInRadius(int count, int km);

  /// No description provided for @directions.
  ///
  /// In fr, this message translates to:
  /// **'Itinéraire'**
  String get directions;

  /// No description provided for @seeDetails.
  ///
  /// In fr, this message translates to:
  /// **'Voir la fiche'**
  String get seeDetails;

  /// No description provided for @locationDisabled.
  ///
  /// In fr, this message translates to:
  /// **'Localisation désactivée sur cet appareil.'**
  String get locationDisabled;

  /// No description provided for @locationDenied.
  ///
  /// In fr, this message translates to:
  /// **'Localisation refusée : la carte reste centrée sur la ville.'**
  String get locationDenied;

  /// No description provided for @myBookings.
  ///
  /// In fr, this message translates to:
  /// **'Mes réservations'**
  String get myBookings;

  /// No description provided for @myBookingsSubtitle.
  ///
  /// In fr, this message translates to:
  /// **'Toutes vos expériences, au même endroit.'**
  String get myBookingsSubtitle;

  /// No description provided for @myCredits.
  ///
  /// In fr, this message translates to:
  /// **'Mes crédits'**
  String get myCredits;

  /// No description provided for @signInToSeeBookings.
  ///
  /// In fr, this message translates to:
  /// **'Connectez-vous pour retrouver vos réservations.'**
  String get signInToSeeBookings;

  /// No description provided for @signInToSeeCredits.
  ///
  /// In fr, this message translates to:
  /// **'Connectez-vous pour voir vos crédits.'**
  String get signInToSeeCredits;

  /// No description provided for @distanceAway.
  ///
  /// In fr, this message translates to:
  /// **'À {distance}'**
  String distanceAway(String distance);

  /// No description provided for @creditsCount.
  ///
  /// In fr, this message translates to:
  /// **'{count, plural, =1{1 crédit} other{{count} crédits}}'**
  String creditsCount(int count);

  /// No description provided for @radiusKm.
  ///
  /// In fr, this message translates to:
  /// **'{km} kilomètres'**
  String radiusKm(int km);

  /// No description provided for @filterDate.
  ///
  /// In fr, this message translates to:
  /// **'Date'**
  String get filterDate;

  /// No description provided for @filterParticipants.
  ///
  /// In fr, this message translates to:
  /// **'Participants'**
  String get filterParticipants;

  /// No description provided for @nextSlotAt.
  ///
  /// In fr, this message translates to:
  /// **'Prochain créneau : {when}'**
  String nextSlotAt(String when);

  /// No description provided for @dateFilterSoon.
  ///
  /// In fr, this message translates to:
  /// **'Le filtre par date arrive bientôt : la carte montre les lieux, les créneaux se choisissent sur la fiche.'**
  String get dateFilterSoon;

  /// No description provided for @participantsFilterSoon.
  ///
  /// In fr, this message translates to:
  /// **'Le filtre par nombre de participants arrive bientôt : il se choisit au moment de réserver.'**
  String get participantsFilterSoon;

  /// No description provided for @recenter.
  ///
  /// In fr, this message translates to:
  /// **'Recentrer la carte'**
  String get recenter;

  /// No description provided for @creditsUnit.
  ///
  /// In fr, this message translates to:
  /// **'crédits'**
  String get creditsUnit;

  /// No description provided for @soonShort.
  ///
  /// In fr, this message translates to:
  /// **'Bientôt'**
  String get soonShort;

  /// No description provided for @myFavorites.
  ///
  /// In fr, this message translates to:
  /// **'Mes favoris'**
  String get myFavorites;

  /// No description provided for @participantsCount.
  ///
  /// In fr, this message translates to:
  /// **'{count, plural, =1{1 personne} other{{count} personnes}}'**
  String participantsCount(int count);

  /// No description provided for @anyDate.
  ///
  /// In fr, this message translates to:
  /// **'N\'importe quand'**
  String get anyDate;

  /// No description provided for @anyParticipants.
  ///
  /// In fr, this message translates to:
  /// **'Tous'**
  String get anyParticipants;

  /// No description provided for @openThatDay.
  ///
  /// In fr, this message translates to:
  /// **'Ouvert ce jour-là'**
  String get openThatDay;

  /// No description provided for @settings.
  ///
  /// In fr, this message translates to:
  /// **'Paramètres'**
  String get settings;

  /// No description provided for @mySpace.
  ///
  /// In fr, this message translates to:
  /// **'Mon espace'**
  String get mySpace;

  /// No description provided for @help.
  ///
  /// In fr, this message translates to:
  /// **'Aide'**
  String get help;

  /// No description provided for @emailAddress.
  ///
  /// In fr, this message translates to:
  /// **'Adresse e-mail'**
  String get emailAddress;

  /// No description provided for @passwordSecurity.
  ///
  /// In fr, this message translates to:
  /// **'Mot de passe et sécurité'**
  String get passwordSecurity;

  /// No description provided for @notifications.
  ///
  /// In fr, this message translates to:
  /// **'Notifications'**
  String get notifications;

  /// No description provided for @pushNotifications.
  ///
  /// In fr, this message translates to:
  /// **'Notifications sur le téléphone'**
  String get pushNotifications;

  /// No description provided for @legalDocs.
  ///
  /// In fr, this message translates to:
  /// **'Conditions et confidentialité'**
  String get legalDocs;

  /// No description provided for @inDrafting.
  ///
  /// In fr, this message translates to:
  /// **'En rédaction'**
  String get inDrafting;

  /// No description provided for @about.
  ///
  /// In fr, this message translates to:
  /// **'À propos'**
  String get about;

  /// No description provided for @appVersion.
  ///
  /// In fr, this message translates to:
  /// **'Version de l’application'**
  String get appVersion;

  /// No description provided for @dangerZone.
  ///
  /// In fr, this message translates to:
  /// **'Zone sensible'**
  String get dangerZone;

  /// No description provided for @settingsSubtitle.
  ///
  /// In fr, this message translates to:
  /// **'Compte, préférences, notifications et confidentialité.'**
  String get settingsSubtitle;

  /// No description provided for @noOffersYet.
  ///
  /// In fr, this message translates to:
  /// **'Cet établissement ne propose aucune prestation pour le moment.'**
  String get noOffersYet;

  /// No description provided for @externalTicket.
  ///
  /// In fr, this message translates to:
  /// **'Billet externe'**
  String get externalTicket;

  /// No description provided for @externalTicketIssued.
  ///
  /// In fr, this message translates to:
  /// **'Le billet est émis par le distributeur partenaire.'**
  String get externalTicketIssued;

  /// No description provided for @nextOpeningSlot.
  ///
  /// In fr, this message translates to:
  /// **'Prochain créneau d’ouverture'**
  String get nextOpeningSlot;

  /// No description provided for @accordingToHours.
  ///
  /// In fr, this message translates to:
  /// **'Selon les horaires. Les places restantes s’affichent dans le calendrier.'**
  String get accordingToHours;

  /// No description provided for @noSlot14Days.
  ///
  /// In fr, this message translates to:
  /// **'Aucun créneau dans les 14 prochains jours'**
  String get noSlot14Days;

  /// No description provided for @ticketAtDistributor.
  ///
  /// In fr, this message translates to:
  /// **'Billet chez le distributeur'**
  String get ticketAtDistributor;

  /// No description provided for @externalTicketNoSlot.
  ///
  /// In fr, this message translates to:
  /// **'Ce billet est émis par le distributeur partenaire : il ne se réserve pas avec un créneau XPASS.'**
  String get externalTicketNoSlot;

  /// No description provided for @seeCalendar.
  ///
  /// In fr, this message translates to:
  /// **'Voir le calendrier'**
  String get seeCalendar;

  /// No description provided for @wheelchairAccessible.
  ///
  /// In fr, this message translates to:
  /// **'Accessible aux personnes à mobilité réduite'**
  String get wheelchairAccessible;

  /// No description provided for @accessibilityNotGuaranteed.
  ///
  /// In fr, this message translates to:
  /// **'Accessibilité non garantie'**
  String get accessibilityNotGuaranteed;

  /// No description provided for @chooseMySlot.
  ///
  /// In fr, this message translates to:
  /// **'Choisir mon créneau'**
  String get chooseMySlot;

  /// No description provided for @availableTimes.
  ///
  /// In fr, this message translates to:
  /// **'Horaires disponibles'**
  String get availableTimes;

  /// No description provided for @noTimeThatDay.
  ///
  /// In fr, this message translates to:
  /// **'Aucun horaire disponible ce jour-là. Essayez une autre date.'**
  String get noTimeThatDay;

  /// No description provided for @holdingSlot.
  ///
  /// In fr, this message translates to:
  /// **'Réservation du créneau…'**
  String get holdingSlot;

  /// No description provided for @noPreference.
  ///
  /// In fr, this message translates to:
  /// **'Sans préférence'**
  String get noPreference;

  /// No description provided for @removeParticipant.
  ///
  /// In fr, this message translates to:
  /// **'Retirer un participant'**
  String get removeParticipant;

  /// No description provided for @addParticipant.
  ///
  /// In fr, this message translates to:
  /// **'Ajouter un participant'**
  String get addParticipant;

  /// No description provided for @confirmBooking.
  ///
  /// In fr, this message translates to:
  /// **'Confirmer la réservation'**
  String get confirmBooking;

  /// No description provided for @checkBeforeConfirm.
  ///
  /// In fr, this message translates to:
  /// **'Vérifiez les détails de votre réservation avant de confirmer.'**
  String get checkBeforeConfirm;

  /// No description provided for @timeExpired.
  ///
  /// In fr, this message translates to:
  /// **'Délai dépassé'**
  String get timeExpired;

  /// No description provided for @slotReleased.
  ///
  /// In fr, this message translates to:
  /// **'Le créneau a été libéré et vos crédits restitués. Choisissez un nouveau créneau.'**
  String get slotReleased;

  /// No description provided for @chooseAnotherSlot.
  ///
  /// In fr, this message translates to:
  /// **'Choisir un autre créneau'**
  String get chooseAnotherSlot;

  /// No description provided for @bookingConfirmed.
  ///
  /// In fr, this message translates to:
  /// **'Réservation confirmée'**
  String get bookingConfirmed;

  /// No description provided for @creditsHeld.
  ///
  /// In fr, this message translates to:
  /// **'Vos crédits sont bloqués, pas encore utilisés.'**
  String get creditsHeld;

  /// No description provided for @freeCancelUntil.
  ///
  /// In fr, this message translates to:
  /// **'Vous pouvez annuler sans frais jusqu’à cette date.'**
  String get freeCancelUntil;

  /// No description provided for @cancelAfterDate.
  ///
  /// In fr, this message translates to:
  /// **'En cas d’annulation après cette date'**
  String get cancelAfterDate;

  /// No description provided for @sessionConfirmed.
  ///
  /// In fr, this message translates to:
  /// **'Votre séance est bien confirmée. À bientôt !'**
  String get sessionConfirmed;

  /// No description provided for @addToCalendar.
  ///
  /// In fr, this message translates to:
  /// **'Ajouter à mon agenda'**
  String get addToCalendar;

  /// No description provided for @writeToVenue.
  ///
  /// In fr, this message translates to:
  /// **'Écrire à l’établissement'**
  String get writeToVenue;

  /// No description provided for @cancelBooking.
  ///
  /// In fr, this message translates to:
  /// **'Annuler la réservation'**
  String get cancelBooking;

  /// No description provided for @needHelp.
  ///
  /// In fr, this message translates to:
  /// **'Besoin d’aide ?'**
  String get needHelp;

  /// No description provided for @cancelBookingQuestion.
  ///
  /// In fr, this message translates to:
  /// **'Annuler la réservation ?'**
  String get cancelBookingQuestion;

  /// No description provided for @cancelledCharged.
  ///
  /// In fr, this message translates to:
  /// **'Réservation annulée, crédits débités.'**
  String get cancelledCharged;

  /// No description provided for @cancelledRefunded.
  ///
  /// In fr, this message translates to:
  /// **'Réservation annulée, crédits restitués.'**
  String get cancelledRefunded;

  /// No description provided for @qrSemantics.
  ///
  /// In fr, this message translates to:
  /// **'QR code de la réservation à présenter au partenaire'**
  String get qrSemantics;

  /// No description provided for @showToPartner.
  ///
  /// In fr, this message translates to:
  /// **'À présenter au partenaire'**
  String get showToPartner;

  /// No description provided for @calendarIntro.
  ///
  /// In fr, this message translates to:
  /// **'Retrouvez les détails de votre réservation dans l’agenda de votre choix.'**
  String get calendarIntro;

  /// No description provided for @chooseCalendar.
  ///
  /// In fr, this message translates to:
  /// **'Choisir un agenda'**
  String get chooseCalendar;

  /// No description provided for @phoneCalendar.
  ///
  /// In fr, this message translates to:
  /// **'Calendrier du téléphone (fichier .ics)'**
  String get phoneCalendar;

  /// No description provided for @reminderSuggested.
  ///
  /// In fr, this message translates to:
  /// **'Rappel suggéré : 1 h avant (inclus dans le fichier .ics)'**
  String get reminderSuggested;

  /// No description provided for @calendarNoQr.
  ///
  /// In fr, this message translates to:
  /// **'L’événement contient l’horaire et l’adresse, jamais votre QR : présentez-le depuis l’application.'**
  String get calendarNoQr;

  /// No description provided for @serviceDoneTitle.
  ///
  /// In fr, this message translates to:
  /// **'Votre prestation est terminée !'**
  String get serviceDoneTitle;

  /// No description provided for @thanksBenefit.
  ///
  /// In fr, this message translates to:
  /// **'Merci d’avoir profité de votre avantage avec XPASS.'**
  String get thanksBenefit;

  /// No description provided for @serviceDone.
  ///
  /// In fr, this message translates to:
  /// **'Prestation effectuée'**
  String get serviceDone;

  /// No description provided for @validatedByPartner.
  ///
  /// In fr, this message translates to:
  /// **'Validée par le partenaire.'**
  String get validatedByPartner;

  /// No description provided for @creditsUsed.
  ///
  /// In fr, this message translates to:
  /// **'Crédits consommés'**
  String get creditsUsed;

  /// No description provided for @receiptReference.
  ///
  /// In fr, this message translates to:
  /// **'Référence du reçu'**
  String get receiptReference;

  /// No description provided for @reviewOnGoogle.
  ///
  /// In fr, this message translates to:
  /// **'Donner mon avis sur Google'**
  String get reviewOnGoogle;

  /// No description provided for @reviewFree.
  ///
  /// In fr, this message translates to:
  /// **'Votre avis est libre et facultatif.'**
  String get reviewFree;

  /// No description provided for @noReviewLink.
  ///
  /// In fr, this message translates to:
  /// **'Cet établissement n’a pas encore renseigné de lien d’avis.'**
  String get noReviewLink;

  /// No description provided for @askForHelp.
  ///
  /// In fr, this message translates to:
  /// **'Demander de l’aide'**
  String get askForHelp;

  /// No description provided for @slotPricePeak.
  ///
  /// In fr, this message translates to:
  /// **'Heure de pointe'**
  String get slotPricePeak;

  /// No description provided for @slotPriceDemand.
  ///
  /// In fr, this message translates to:
  /// **'Forte demande'**
  String get slotPriceDemand;

  /// No description provided for @slotPriceLastMinute.
  ///
  /// In fr, this message translates to:
  /// **'Dernière minute'**
  String get slotPriceLastMinute;

  /// No description provided for @slotPriceLegend.
  ///
  /// In fr, this message translates to:
  /// **'Le prix varie selon l’heure et la demande : ↑ heure de pointe ou forte demande, ↓ dernière minute.'**
  String get slotPriceLegend;

  /// No description provided for @lateCancelInfo.
  ///
  /// In fr, this message translates to:
  /// **'Après ce délai, une annulation vous rend {refund} sur {total} (la moitié). Sans annulation ni présentation, tout est consommé.'**
  String lateCancelInfo(String refund, String total);

  /// No description provided for @cancelledPartlyRefunded.
  ///
  /// In fr, this message translates to:
  /// **'Réservation annulée : {refund} vous ont été rendus.'**
  String cancelledPartlyRefunded(String refund);

  /// No description provided for @creditRulesTitle.
  ///
  /// In fr, this message translates to:
  /// **'Comment fonctionnent vos crédits'**
  String get creditRulesTitle;

  /// No description provided for @creditRulePrice.
  ///
  /// In fr, this message translates to:
  /// **'Le prix d’un créneau varie : plus cher aux heures de pointe (↑), moins cher en dernière minute (↓). Il est fixé au moment de la réservation.'**
  String get creditRulePrice;

  /// No description provided for @creditRuleCancel.
  ///
  /// In fr, this message translates to:
  /// **'Annulation gratuite jusqu’au délai indiqué ; après, la moitié des crédits vous est rendue. Sans annulation ni présentation, tout est consommé.'**
  String get creditRuleCancel;

  /// No description provided for @creditRuleRollover.
  ///
  /// In fr, this message translates to:
  /// **'Crédits d’abonnement non utilisés : reportés au mois suivant jusqu’à un mois de formule ; ils expirent à l’arrêt de l’abonnement.'**
  String get creditRuleRollover;

  /// No description provided for @creditRuleEmployer.
  ///
  /// In fr, this message translates to:
  /// **'Crédits offerts par votre employeur : utilisés en priorité, selon la durée de validité fixée par l’entreprise.'**
  String get creditRuleEmployer;

  /// No description provided for @madeByAlystra.
  ///
  /// In fr, this message translates to:
  /// **'Réalisée par Alystra'**
  String get madeByAlystra;

  /// No description provided for @pushNotificationsHint.
  ///
  /// In fr, this message translates to:
  /// **'Alertes de réservation, de paiement et de messages'**
  String get pushNotificationsHint;

  /// No description provided for @noNotifications.
  ///
  /// In fr, this message translates to:
  /// **'Aucune notification pour le moment.'**
  String get noNotifications;

  /// No description provided for @notificationsSubtitle.
  ///
  /// In fr, this message translates to:
  /// **'Réservations, paiements et réponses de l’équipe.'**
  String get notificationsSubtitle;
}

class _AppLocalizationsDelegate
    extends LocalizationsDelegate<AppLocalizations> {
  const _AppLocalizationsDelegate();

  @override
  Future<AppLocalizations> load(Locale locale) {
    return SynchronousFuture<AppLocalizations>(lookupAppLocalizations(locale));
  }

  @override
  bool isSupported(Locale locale) =>
      <String>['ar', 'en', 'fr'].contains(locale.languageCode);

  @override
  bool shouldReload(_AppLocalizationsDelegate old) => false;
}

AppLocalizations lookupAppLocalizations(Locale locale) {
  // Lookup logic when only language code is specified.
  switch (locale.languageCode) {
    case 'ar':
      return AppLocalizationsAr();
    case 'en':
      return AppLocalizationsEn();
    case 'fr':
      return AppLocalizationsFr();
  }

  throw FlutterError(
      'AppLocalizations.delegate failed to load unsupported locale "$locale". This is likely '
      'an issue with the localizations generation tool. Please file an issue '
      'on GitHub with a reproducible sample app and the gen-l10n configuration '
      'that was used.');
}
