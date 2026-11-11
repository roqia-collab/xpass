// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for French (`fr`).
class AppLocalizationsFr extends AppLocalizations {
  AppLocalizationsFr([String locale = 'fr']) : super(locale);

  @override
  String get navExplore => 'Explorer';

  @override
  String get navBookings => 'Réservations';

  @override
  String get navCredits => 'Mes crédits';

  @override
  String get navProfile => 'Paramètres';

  @override
  String get retry => 'Réessayer';

  @override
  String get unexpectedError => 'Une erreur inattendue est survenue.';

  @override
  String get comingSoon => 'Bientôt disponible';

  @override
  String get understood => 'Compris';

  @override
  String get loading => 'Chargement';

  @override
  String get back => 'Retour';

  @override
  String get chooseCity => 'Choisir une ville';

  @override
  String get nearYou => 'À réserver près de vous';

  @override
  String get seeAll => 'Voir tout';

  @override
  String get seeOnMap => 'Voir sur la carte';

  @override
  String get homeSearchHint => 'Yoga, concert, spa, musée…';

  @override
  String get todayChip => 'Aujourd\'hui';

  @override
  String get tomorrowChip => 'Demain';

  @override
  String get allUniverses => 'Tout';

  @override
  String get noSlotsThatDay =>
      'Aucun créneau à cette date. Changez de jour ou d’univers.';

  @override
  String get welcomeTitle => 'Un pass, toutes vos envies';

  @override
  String get welcomeSubtitle =>
      'Sport, culture, beauté et sorties — réservez avec des crédits, près de chez vous.';

  @override
  String get signIn => 'Continuer avec Google';

  @override
  String get signInHint =>
      'Connectez-vous pour réserver avec vos crédits, dans tous les univers.';

  @override
  String get or => 'ou';

  @override
  String get createAccount => 'Créer un compte';

  @override
  String get signInEmail => 'Continuer avec un e-mail';

  @override
  String get createAccountEmail => 'Créer un compte avec un e-mail';

  @override
  String get passwordNotice =>
      'Google ou e-mail, sur la page sécurisée. L’application ne voit jamais votre mot de passe.';

  @override
  String get exploreWithoutAccount => 'Explorer sans compte';

  @override
  String get demoMode => 'Mode démonstration';

  @override
  String get legalPending =>
      'Conditions générales et politique de confidentialité : documents en cours de rédaction.';

  @override
  String get myProfile => 'Paramètres';

  @override
  String get profileSubtitle =>
      'Compte, préférences, notifications et confidentialité.';

  @override
  String get emailVerified => 'Adresse e-mail vérifiée';

  @override
  String get emailNotVerified => 'Compte de démonstration (e-mail non vérifié)';

  @override
  String get account => 'Compte';

  @override
  String get personalInfo => 'Informations personnelles';

  @override
  String get country => 'Pays';

  @override
  String get france => 'France';

  @override
  String get mySubscription => 'Mon abonnement';

  @override
  String get preferences => 'Préférences';

  @override
  String get language => 'Langue';

  @override
  String get bookingEmails => 'E-mails de réservation';

  @override
  String get bookingEmailsHint => 'Confirmations, annulations et reçus';

  @override
  String get support => 'Assistance';

  @override
  String get helpCenter => 'Centre d’aide';

  @override
  String get contactSupport => 'Contacter le support';

  @override
  String get myRequests => 'Mes demandes';

  @override
  String get privacy => 'Confidentialité';

  @override
  String get locationPermission => 'Permissions localisation';

  @override
  String get cameraPermission => 'Permissions caméra';

  @override
  String get optional => 'Optionnel';

  @override
  String get exportData => 'Exporter mes données';

  @override
  String get deleteAccount => 'Supprimer mon compte';

  @override
  String get permissionsNotice =>
      'La localisation et la caméra sont optionnelles : elles ne sont demandées qu’au moment de les utiliser (carte « Autour de moi »), et vous pouvez les refuser dans les réglages de votre téléphone.';

  @override
  String get signOut => 'Se déconnecter';

  @override
  String get translationNotice =>
      'Les contenus des établissements restent dans leur langue d’origine.';

  @override
  String get nearbyTitle => 'Autour de moi';

  @override
  String get nearbySubtitle => 'Trouvez des expériences près de chez vous';

  @override
  String get myPosition => 'Ma position';

  @override
  String get locateMe => 'Me localiser';

  @override
  String get locating => 'Localisation…';

  @override
  String get category => 'Catégorie';

  @override
  String get allCategories => 'Toutes';

  @override
  String get budget => 'Budget';

  @override
  String get anyBudget => 'Tous';

  @override
  String upToCredits(int count) {
    return '≤ $count crédits';
  }

  @override
  String get searchThisArea => 'Rechercher dans cette zone';

  @override
  String get noResultsArea =>
      'Aucune expérience dans cette zone : élargissez le rayon ou changez les filtres.';

  @override
  String get loadPlacesError => 'Impossible de charger les lieux.';

  @override
  String placesInRadius(int count, int km) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count lieux',
      one: '1 lieu',
    );
    return '$_temp0 dans un rayon de $km km. Touchez un prix pour voir la fiche.';
  }

  @override
  String get directions => 'Itinéraire';

  @override
  String get seeDetails => 'Voir la fiche';

  @override
  String get locationDisabled => 'Localisation désactivée sur cet appareil.';

  @override
  String get locationDenied =>
      'Localisation refusée : la carte reste centrée sur la ville.';

  @override
  String get myBookings => 'Mes réservations';

  @override
  String get myBookingsSubtitle => 'Toutes vos expériences, au même endroit.';

  @override
  String get myCredits => 'Mes crédits';

  @override
  String get signInToSeeBookings =>
      'Connectez-vous pour retrouver vos réservations.';

  @override
  String get signInToSeeCredits => 'Connectez-vous pour voir vos crédits.';

  @override
  String distanceAway(String distance) {
    return 'À $distance';
  }

  @override
  String creditsCount(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count crédits',
      one: '1 crédit',
    );
    return '$_temp0';
  }

  @override
  String radiusKm(int km) {
    return '$km kilomètres';
  }

  @override
  String get filterDate => 'Date';

  @override
  String get filterParticipants => 'Participants';

  @override
  String nextSlotAt(String when) {
    return 'Prochain créneau : $when';
  }

  @override
  String get dateFilterSoon =>
      'Le filtre par date arrive bientôt : la carte montre les lieux, les créneaux se choisissent sur la fiche.';

  @override
  String get participantsFilterSoon =>
      'Le filtre par nombre de participants arrive bientôt : il se choisit au moment de réserver.';

  @override
  String get recenter => 'Recentrer la carte';

  @override
  String get creditsUnit => 'crédits';

  @override
  String get soonShort => 'Bientôt';

  @override
  String get myFavorites => 'Mes favoris';

  @override
  String participantsCount(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count personnes',
      one: '1 personne',
    );
    return '$_temp0';
  }

  @override
  String get anyDate => 'N\'importe quand';

  @override
  String get anyParticipants => 'Tous';

  @override
  String get openThatDay => 'Ouvert ce jour-là';

  @override
  String get settings => 'Paramètres';

  @override
  String get mySpace => 'Mon espace';

  @override
  String get help => 'Aide';

  @override
  String get emailAddress => 'Adresse e-mail';

  @override
  String get passwordSecurity => 'Mot de passe et sécurité';

  @override
  String get notifications => 'Notifications';

  @override
  String get pushNotifications => 'Notifications sur le téléphone';

  @override
  String get legalDocs => 'Conditions et confidentialité';

  @override
  String get inDrafting => 'En rédaction';

  @override
  String get about => 'À propos';

  @override
  String get appVersion => 'Version de l’application';

  @override
  String get dangerZone => 'Zone sensible';

  @override
  String get settingsSubtitle =>
      'Compte, préférences, notifications et confidentialité.';

  @override
  String get noOffersYet =>
      'Cet établissement ne propose aucune prestation pour le moment.';

  @override
  String get externalTicket => 'Billet externe';

  @override
  String get externalTicketIssued =>
      'Le billet est émis par le distributeur partenaire.';

  @override
  String get nextOpeningSlot => 'Prochain créneau d’ouverture';

  @override
  String get accordingToHours =>
      'Selon les horaires. Les places restantes s’affichent dans le calendrier.';

  @override
  String get noSlot14Days => 'Aucun créneau dans les 14 prochains jours';

  @override
  String get ticketAtDistributor => 'Billet chez le distributeur';

  @override
  String get externalTicketNoSlot =>
      'Ce billet est émis par le distributeur partenaire : il ne se réserve pas avec un créneau XPASS.';

  @override
  String get seeCalendar => 'Voir le calendrier';

  @override
  String get wheelchairAccessible =>
      'Accessible aux personnes à mobilité réduite';

  @override
  String get accessibilityNotGuaranteed => 'Accessibilité non garantie';

  @override
  String get chooseMySlot => 'Choisir mon créneau';

  @override
  String get availableTimes => 'Horaires disponibles';

  @override
  String get noTimeThatDay =>
      'Aucun horaire disponible ce jour-là. Essayez une autre date.';

  @override
  String get holdingSlot => 'Réservation du créneau…';

  @override
  String get noPreference => 'Sans préférence';

  @override
  String get removeParticipant => 'Retirer un participant';

  @override
  String get addParticipant => 'Ajouter un participant';

  @override
  String get confirmBooking => 'Confirmer la réservation';

  @override
  String get checkBeforeConfirm =>
      'Vérifiez les détails de votre réservation avant de confirmer.';

  @override
  String get timeExpired => 'Délai dépassé';

  @override
  String get slotReleased =>
      'Le créneau a été libéré et vos crédits restitués. Choisissez un nouveau créneau.';

  @override
  String get chooseAnotherSlot => 'Choisir un autre créneau';

  @override
  String get bookingConfirmed => 'Réservation confirmée';

  @override
  String get creditsHeld => 'Vos crédits sont bloqués, pas encore utilisés.';

  @override
  String get freeCancelUntil =>
      'Vous pouvez annuler sans frais jusqu’à cette date.';

  @override
  String get cancelAfterDate => 'En cas d’annulation après cette date';

  @override
  String get sessionConfirmed => 'Votre séance est bien confirmée. À bientôt !';

  @override
  String get addToCalendar => 'Ajouter à mon agenda';

  @override
  String get writeToVenue => 'Écrire à l’établissement';

  @override
  String get cancelBooking => 'Annuler la réservation';

  @override
  String get needHelp => 'Besoin d’aide ?';

  @override
  String get cancelBookingQuestion => 'Annuler la réservation ?';

  @override
  String get cancelledCharged => 'Réservation annulée, crédits débités.';

  @override
  String get cancelledRefunded => 'Réservation annulée, crédits restitués.';

  @override
  String get qrSemantics =>
      'QR code de la réservation à présenter au partenaire';

  @override
  String get showToPartner => 'À présenter au partenaire';

  @override
  String get calendarIntro =>
      'Retrouvez les détails de votre réservation dans l’agenda de votre choix.';

  @override
  String get chooseCalendar => 'Choisir un agenda';

  @override
  String get phoneCalendar => 'Calendrier du téléphone (fichier .ics)';

  @override
  String get reminderSuggested =>
      'Rappel suggéré : 1 h avant (inclus dans le fichier .ics)';

  @override
  String get calendarNoQr =>
      'L’événement contient l’horaire et l’adresse, jamais votre QR : présentez-le depuis l’application.';

  @override
  String get serviceDoneTitle => 'Votre prestation est terminée !';

  @override
  String get thanksBenefit =>
      'Merci d’avoir profité de votre avantage avec XPASS.';

  @override
  String get serviceDone => 'Prestation effectuée';

  @override
  String get validatedByPartner => 'Validée par le partenaire.';

  @override
  String get creditsUsed => 'Crédits consommés';

  @override
  String get receiptReference => 'Référence du reçu';

  @override
  String get reviewOnGoogle => 'Donner mon avis sur Google';

  @override
  String get reviewFree => 'Votre avis est libre et facultatif.';

  @override
  String get noReviewLink =>
      'Cet établissement n’a pas encore renseigné de lien d’avis.';

  @override
  String get askForHelp => 'Demander de l’aide';

  @override
  String get slotPricePeak => 'Heure de pointe';

  @override
  String get slotPriceDemand => 'Forte demande';

  @override
  String get slotPriceLastMinute => 'Dernière minute';

  @override
  String get slotPriceLegend =>
      'Le prix varie selon l’heure et la demande : ↑ heure de pointe ou forte demande, ↓ dernière minute.';

  @override
  String lateCancelInfo(String refund, String total) {
    return 'Après ce délai, une annulation vous rend $refund sur $total (la moitié). Sans annulation ni présentation, tout est consommé.';
  }

  @override
  String cancelledPartlyRefunded(String refund) {
    return 'Réservation annulée : $refund vous ont été rendus.';
  }

  @override
  String get creditRulesTitle => 'Comment fonctionnent vos crédits';

  @override
  String get creditRulePrice =>
      'Le prix d’un créneau varie : plus cher aux heures de pointe (↑), moins cher en dernière minute (↓). Il est fixé au moment de la réservation.';

  @override
  String get creditRuleCancel =>
      'Annulation gratuite jusqu’au délai indiqué ; après, la moitié des crédits vous est rendue. Sans annulation ni présentation, tout est consommé.';

  @override
  String get creditRuleRollover =>
      'Crédits d’abonnement non utilisés : reportés au mois suivant jusqu’à un mois de formule ; ils expirent à l’arrêt de l’abonnement.';

  @override
  String get creditRuleEmployer =>
      'Crédits offerts par votre employeur : utilisés en priorité, selon la durée de validité fixée par l’entreprise.';

  @override
  String get madeByAlystra => 'Réalisée par Alystra';

  @override
  String get pushNotificationsHint =>
      'Alertes de réservation, de paiement et de messages';

  @override
  String get noNotifications => 'Aucune notification pour le moment.';

  @override
  String get notificationsSubtitle =>
      'Réservations, paiements et réponses de l’équipe.';
}
