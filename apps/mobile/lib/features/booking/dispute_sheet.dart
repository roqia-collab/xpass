import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api_client.dart';
import '../../core/theme.dart';
import 'booking_repository.dart';

/// Réclamation sur une prestation utilisée : examinée par l'équipe XPASS (aucune restitution automatique).
Future<void> showDisputeSheet(BuildContext context, String bookingId) => showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: XColors.cream,
      builder: (_) => Padding(
        padding: EdgeInsets.only(bottom: MediaQuery.of(context).viewInsets.bottom),
        child: DisputeForm(bookingId: bookingId),
      ),
    );

class DisputeForm extends ConsumerStatefulWidget {
  const DisputeForm({super.key, required this.bookingId});
  final String bookingId;

  @override
  ConsumerState<DisputeForm> createState() => _DisputeFormState();
}

class _DisputeFormState extends ConsumerState<DisputeForm> {
  final _reason = TextEditingController();
  bool _busy = false;
  String? _error;

  @override
  void dispose() {
    _reason.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await ref.read(bookingRepositoryProvider).openDispute(widget.bookingId, _reason.text.trim());
      ref.invalidate(disputesProvider(widget.bookingId));
      if (mounted) Navigator.of(context).pop();
    } on ApiException catch (e) {
      setState(() => _error = e.message);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final existing = ref.watch(disputesProvider(widget.bookingId)).valueOrNull ?? const [];
    final current = existing.isEmpty ? null : existing.first;
    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Text('Demander de l’aide', style: serif(28)),
          const SizedBox(height: 8),
          if (current != null && current.isOpen) ...[
            Text('Réclamation ${current.reference} en cours d’examen par l’équipe XPASS.',
                style: const TextStyle(fontWeight: FontWeight.w600)),
            const SizedBox(height: 6),
            const Text('Vous serez informé(e) de la décision dans l’application.',
                style: TextStyle(color: XColors.navyMuted)),
          ] else ...[
            if (current != null)
              Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: Text(current.summary, style: const TextStyle(color: XColors.navyMuted)),
              ),
            const Text(
                'Décrivez le problème rencontré lors de la prestation. L’équipe XPASS examine chaque réclamation.',
                style: TextStyle(color: XColors.navyMuted)),
            const SizedBox(height: 12),
            TextField(
              controller: _reason,
              maxLines: 4,
              maxLength: 2000,
              decoration: InputDecoration(
                labelText: 'Votre réclamation',
                filled: true,
                fillColor: Colors.white,
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(16)),
              ),
            ),
            if (_error != null) Text(_error!, style: const TextStyle(color: Color(0xFFB42318))),
            const SizedBox(height: 8),
            FilledButton(
              onPressed: _busy ? null : _submit,
              child: Text(_busy ? 'Envoi…' : 'Envoyer la réclamation'),
            ),
          ],
        ]),
      ),
    );
  }
}
