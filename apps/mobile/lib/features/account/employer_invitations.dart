import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api_client.dart';
import '../../core/theme.dart';
import '../booking/booking_repository.dart';

/// Avantage salarié : l'invitation de l'employeur s'accepte ici, avec le compte de l'adresse invitée.
class EmployerInvitations extends ConsumerStatefulWidget {
  const EmployerInvitations({super.key});

  @override
  ConsumerState<EmployerInvitations> createState() => _EmployerInvitationsState();
}

class _EmployerInvitationsState extends ConsumerState<EmployerInvitations> {
  bool _busy = false;

  Future<void> _accept(String id, String organization) async {
    setState(() => _busy = true);
    try {
      await ref.read(bookingRepositoryProvider).acceptEmployerInvitation(id);
      ref.invalidate(employerInvitationsProvider);
      invalidateBookingData(ref);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text('Avantage $organization activé. Vos crédits employeur apparaissent dans « Mes crédits » '
              'dès que le financement de votre entreprise le permet.'),
        ));
      }
    } on ApiException catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.message)));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final invitations = ref.watch(employerInvitationsProvider).valueOrNull ?? const [];
    return Column(children: [
      for (final (id, organization) in invitations)
        Container(
          margin: const EdgeInsets.only(top: 12),
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(color: XColors.mint, borderRadius: BorderRadius.circular(XRadius.card)),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            const Row(children: [
              Icon(Icons.apartment),
              SizedBox(width: 8),
              Text('Avantage salarié', style: TextStyle(fontWeight: FontWeight.w700)),
            ]),
            const SizedBox(height: 6),
            Text('$organization vous invite à profiter de crédits XPASS financés par votre employeur.'),
            const SizedBox(height: 6),
            const Text('Votre employeur ne voit pas le détail de vos réservations.',
                style: TextStyle(fontSize: 13, color: XColors.navyMuted)),
            const SizedBox(height: 10),
            FilledButton(
              onPressed: _busy ? null : () => _accept(id, organization),
              child: Text(_busy ? 'Activation…' : 'Accepter l’invitation'),
            ),
          ]),
        ),
    ]);
  }
}
