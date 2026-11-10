import 'package:go_router/go_router.dart';

import '../features/explore/category_screen.dart';
import '../features/explore/home_screen.dart';
import '../features/explore/location_screen.dart';
import '../features/explore/search_screen.dart';
import '../features/account/notifications_screen.dart';
import '../features/account/profile_screen.dart';
import '../features/account/subscription_screen.dart';
import '../features/booking/booking_detail_screen.dart';
import '../features/booking/bookings_screen.dart';
import '../features/booking/receipt_screen.dart';
import '../features/booking/calendar_screen.dart';
import '../features/booking/confirm_screen.dart';
import '../features/booking/credits_screen.dart';
import '../features/explore/nearby_screen.dart';
import '../features/shell/app_shell.dart';
import '../features/engagement/engagement.dart';

final appRouter = GoRouter(
  initialLocation: '/explore',
  routes: [
    StatefulShellRoute.indexedStack(
      builder: (context, state, shell) => AppShell(shell: shell),
      branches: [
        StatefulShellBranch(routes: [
          GoRoute(
            path: '/explore',
            builder: (_, __) => const HomeScreen(),
            routes: [
              GoRoute(path: 'univers/:slug', builder: (_, s) => CategoryScreen(slug: s.pathParameters['slug']!)),
              GoRoute(
                path: 'autour',
                builder: (_, s) => NearbyScreen(initialCategory: s.uri.queryParameters['categorie']),
              ),
              GoRoute(
                path: 'lieu/:slug',
                builder: (_, s) => LocationScreen(slug: s.pathParameters['slug']!),
                routes: [
                  GoRoute(
                    path: 'reserver/:offerId',
                    builder: (_, s) =>
                        CalendarScreen(locationSlug: s.pathParameters['slug']!, offerId: s.pathParameters['offerId']!),
                  ),
                ],
              ),
              GoRoute(path: 'reservation/:id', builder: (_, s) => ConfirmScreen(bookingId: s.pathParameters['id']!)),
              GoRoute(path: 'recherche', builder: (_, s) => SearchScreen(initialQuery: s.uri.queryParameters['q'])),
            ],
          ),
        ]),
        StatefulShellBranch(routes: [
          GoRoute(
            path: '/reservations',
            builder: (_, __) => const BookingsScreen(),
            routes: [
              GoRoute(
                path: ':id',
                builder: (_, s) => BookingDetailScreen(bookingId: s.pathParameters['id']!),
                routes: [
                  GoRoute(path: 'recu', builder: (_, s) => ReceiptScreen(bookingId: s.pathParameters['id']!)),
                  GoRoute(path: 'messages', builder: (_, s) => MessagesScreen(bookingId: s.pathParameters['id']!)),
                ],
              ),
            ],
          ),
        ]),
        StatefulShellBranch(routes: [
          GoRoute(path: '/credits', builder: (_, __) => const CreditsScreen()),
        ]),
        StatefulShellBranch(routes: [
          GoRoute(
            path: '/profil',
            builder: (_, __) => const ProfileScreen(),
            routes: [
              GoRoute(path: 'favoris', builder: (_, __) => const FavoritesScreen()),
              GoRoute(path: 'notifications', builder: (_, __) => const NotificationsScreen()),
              GoRoute(path: 'parametres', redirect: (_, __) => '/profil'),
            ],
          ),
          // Adresse de retour du paiement hébergé : /#/abonnement?retour=paiement
          GoRoute(
            path: '/abonnement',
            builder: (_, s) => SubscriptionScreen(returnedFrom: s.uri.queryParameters['retour']),
          ),
        ]),
      ],
    ),
  ],
);
