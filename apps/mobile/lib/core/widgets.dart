import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../features/catalog/catalog_repository.dart';
import 'api_client.dart';
import 'config.dart';
import 'theme.dart';
import 'l10n.dart';

/// Icônes cohérentes pour les sous-catégories (clé `icon` renvoyée par l'API).
IconData subcategoryIcon(String key) => switch (key) {
      'attractions' => Icons.attractions_outlined,
      'movie' => Icons.movie_outlined,
      'theater' => Icons.theater_comedy_outlined,
      'fitness' => Icons.fitness_center,
      'dance' => Icons.directions_walk,
      'yoga' => Icons.self_improvement,
      'climbing' => Icons.terrain_outlined,
      'museum' => Icons.account_balance_outlined,
      'palette' => Icons.palette_outlined,
      'pottery' => Icons.emoji_objects_outlined,
      'scissors' => Icons.content_cut,
      'nails' => Icons.back_hand_outlined,
      'spa' => Icons.spa_outlined,
      _ => Icons.local_activity_outlined,
    };

IconData categoryIcon(String slug) => switch (slug) {
      'divertissement' => Icons.celebration_outlined,
      'sport' => Icons.directions_run,
      'culture' => Icons.museum_outlined,
      'beaute' => Icons.spa_outlined,
      _ => Icons.local_activity_outlined,
    };

class XpassLogo extends StatelessWidget {
  const XpassLogo({super.key, this.height = 30});
  final double height;

  @override
  Widget build(BuildContext context) => Semantics(
        label: 'XPASS',
        child: Image.asset('assets/brand/logo.png', height: height, fit: BoxFit.contain),
      );
}

/// Photo distante avec repli explicite (dégradé + icône) si le média est absent ou inaccessible.
class MediaImage extends StatelessWidget {
  const MediaImage({super.key, required this.imageKey, this.fallbackIcon = Icons.image_outlined, this.semanticLabel});

  final String? imageKey;
  final IconData fallbackIcon;
  final String? semanticLabel;

  @override
  Widget build(BuildContext context) {
    final url = AppConfig.mediaUrl(imageKey);
    final fallback = DecoratedBox(
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          colors: [XColors.navy, Color(0xFF3D4A6B)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
      ),
      child: Center(child: Icon(fallbackIcon, size: 40, color: Colors.white70)),
    );
    if (url == null) return SizedBox.expand(child: fallback);
    return Image.network(
      url,
      fit: BoxFit.cover,
      width: double.infinity,
      height: double.infinity,
      semanticLabel: semanticLabel,
      errorBuilder: (_, __, ___) => SizedBox.expand(child: fallback),
      loadingBuilder: (context, child, progress) =>
          progress == null ? child : const ColoredBox(color: XColors.creamDark, child: SizedBox.expand()),
    );
  }
}

/// Photo d'en-tête des maquettes : bord courbe côté texte, fondue dans le fond crème.
class FadedPhoto extends StatelessWidget {
  const FadedPhoto({super.key, required this.imageKey, this.fadeStop = 0.38});
  final String? imageKey;
  final double fadeStop;

  @override
  Widget build(BuildContext context) {
    final dir = Directionality.of(context);
    return ExcludeSemantics(
      child: ClipRRect(
        borderRadius: const BorderRadiusDirectional.only(
          bottomStart: Radius.circular(200),
          topStart: Radius.circular(110),
        ).resolve(dir),
        child: ShaderMask(
          blendMode: BlendMode.dstIn,
          shaderCallback: (rect) => LinearGradient(
            begin: AlignmentDirectional.centerStart.resolve(dir),
            end: AlignmentDirectional.centerEnd.resolve(dir),
            colors: const [Colors.transparent, Colors.black],
            stops: [0, fadeStop],
          ).createShader(rect),
          child: MediaImage(imageKey: imageKey),
        ),
      ),
    );
  }
}

/// En-tête avec photo à droite (maquettes 12 à 16) ; [child] (titre, sous-titre) passe par-dessus, à gauche.
/// La photo déborde du rembourrage de la liste ([bleed]) pour toucher le bord de l'écran.
class PhotoHeader extends StatelessWidget {
  const PhotoHeader({
    super.key,
    required this.imageKey,
    required this.child,
    this.widthFactor = 0.55,
    this.height = 230,
    this.bleed = 20,
    this.top = -12,
  });
  final String imageKey;
  final Widget child;
  final double widthFactor;
  final double height;
  final double bleed;
  final double top;

  @override
  Widget build(BuildContext context) => Stack(clipBehavior: Clip.none, children: [
        PositionedDirectional(
          top: top,
          end: -bleed,
          width: MediaQuery.sizeOf(context).width * widthFactor,
          height: height,
          child: FadedPhoto(imageKey: imageKey),
        ),
        child,
      ]);
}

class CityChip extends ConsumerWidget {
  const CityChip({super.key, this.background, this.onDark = false});
  final Color? background;
  final bool onDark;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final city = ref.watch(selectedCityProvider);
    return Material(
      color: background ?? (onDark ? Colors.white12 : Colors.transparent),
      shape: const StadiumBorder(),
      child: InkWell(
        customBorder: const StadiumBorder(),
        onTap: () => _pickCity(context, ref),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          child: Row(mainAxisSize: MainAxisSize.min, children: [
            Icon(Icons.location_on_outlined, size: 20, color: onDark ? Colors.white : XColors.navy),
            const SizedBox(width: 4),
            Text(city.name,
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600, color: onDark ? Colors.white : XColors.navy)),
            Icon(Icons.keyboard_arrow_down, color: onDark ? Colors.white : XColors.navy),
          ]),
        ),
      ),
    );
  }

  Future<void> _pickCity(BuildContext context, WidgetRef ref) async {
    await showModalBottomSheet<void>(
      context: context,
      backgroundColor: XColors.cream,
      builder: (context) => Consumer(builder: (context, ref, _) {
        final cities = ref.watch(citiesProvider);
        return SafeArea(
          child: cities.when(
            loading: () => const Padding(padding: EdgeInsets.all(32), child: LoadingView()),
            error: (e, _) => ErrorView(error: e, onRetry: () => ref.invalidate(citiesProvider)),
            data: (list) => ListView(shrinkWrap: true, children: [
              Padding(padding: const EdgeInsets.all(20), child: Text(context.l10n.chooseCity, style: serif(26))),
              for (final c in list)
                ListTile(
                  title: Text(c.name),
                  trailing: c.slug == ref.read(selectedCityProvider).slug ? const Icon(Icons.check) : null,
                  onTap: () {
                    ref.read(selectedCityProvider.notifier).state = c;
                    Navigator.pop(context);
                  },
                ),
            ]),
          ),
        );
      }),
    );
  }
}

class LoadingView extends StatelessWidget {
  const LoadingView({super.key});

  @override
  Widget build(BuildContext context) =>
      Center(child: CircularProgressIndicator(color: XColors.coral, semanticsLabel: context.l10n.loading));
}

class ErrorView extends StatelessWidget {
  const ErrorView({super.key, required this.error, required this.onRetry});
  final Object error;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final network = error is ApiException && (error as ApiException).isNetwork;
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          Icon(network ? Icons.wifi_off_rounded : Icons.error_outline, size: 40, color: XColors.navyMuted),
          const SizedBox(height: 12),
          Text(error is ApiException ? error.toString() : context.l10n.unexpectedError, textAlign: TextAlign.center),
          const SizedBox(height: 16),
          OutlinedButton(onPressed: onRetry, child: Text(context.l10n.retry)),
        ]),
      ),
    );
  }
}

class EmptyView extends StatelessWidget {
  const EmptyView({super.key, required this.message});
  final String message;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 40, horizontal: 24),
        child: Column(children: [
          const Icon(Icons.search_off_rounded, size: 40, color: XColors.navyMuted),
          const SizedBox(height: 12),
          Text(message, textAlign: TextAlign.center, style: const TextStyle(color: XColors.navyMuted)),
        ]),
      );
}

/// Fonctionnalité non livrée : on l'indique clairement, sans simuler de résultat.
Future<void> showComingSoon(BuildContext context, {required String title, required String body}) {
  return showModalBottomSheet<void>(
    context: context,
    backgroundColor: XColors.cream,
    builder: (context) => SafeArea(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(24, 24, 24, 16),
        child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
            decoration: BoxDecoration(color: XColors.lavender, borderRadius: BorderRadius.circular(12)),
            child: Text(context.l10n.comingSoon, style: const TextStyle(fontWeight: FontWeight.w600)),
          ),
          const SizedBox(height: 12),
          Text(title, style: serif(26)),
          const SizedBox(height: 8),
          Text(body, style: const TextStyle(fontSize: 15, color: XColors.navyMuted, height: 1.4)),
          const SizedBox(height: 20),
          FilledButton(onPressed: () => Navigator.pop(context), child: Text(context.l10n.understood)),
        ]),
      ),
    ),
  );
}

class CoralButton extends StatelessWidget {
  const CoralButton({super.key, required this.label, required this.onPressed, this.icon});
  final String label;
  final VoidCallback? onPressed;
  final IconData? icon;

  @override
  Widget build(BuildContext context) => FilledButton(
        onPressed: onPressed,
        child: Row(mainAxisAlignment: MainAxisAlignment.center, children: [
          if (icon != null) ...[Icon(icon, size: 22), const SizedBox(width: 10)],
          Flexible(child: Text(label, overflow: TextOverflow.ellipsis)),
          const SizedBox(width: 8),
          const Icon(Icons.chevron_right),
        ]),
      );
}

/// Retour tactile premium : l'élément se resserre légèrement sous le doigt (désactivé si « réduire les animations »).
class Pressable extends StatefulWidget {
  const Pressable({super.key, required this.child, required this.onTap, this.scale = 0.97});
  final Widget child;
  final VoidCallback? onTap;
  final double scale;

  @override
  State<Pressable> createState() => _PressableState();
}

class _PressableState extends State<Pressable> {
  bool _down = false;

  void _set(bool v) {
    if (_down != v && !MediaQuery.of(context).disableAnimations) setState(() => _down = v);
  }

  @override
  Widget build(BuildContext context) => GestureDetector(
        onTapDown: widget.onTap == null ? null : (_) => _set(true),
        onTapUp: widget.onTap == null ? null : (_) => _set(false),
        onTapCancel: () => _set(false),
        child: AnimatedScale(
          scale: _down ? widget.scale : 1,
          duration: const Duration(milliseconds: 120),
          curve: Curves.easeOut,
          child: widget.child,
        ),
      );
}

/// Photo qui s’avance lentement (effet travelling). Immobile si les animations sont réduites.
class KenBurnsPhoto extends StatefulWidget {
  const KenBurnsPhoto({super.key, required this.imageKey, this.fallbackIcon = Icons.image_outlined});
  final String? imageKey;
  final IconData fallbackIcon;

  @override
  State<KenBurnsPhoto> createState() => _KenBurnsPhotoState();
}

class _KenBurnsPhotoState extends State<KenBurnsPhoto> with SingleTickerProviderStateMixin {
  late final AnimationController _c = AnimationController(vsync: this, duration: const Duration(seconds: 16))
    ..repeat(reverse: true);

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final photo = MediaImage(imageKey: widget.imageKey, fallbackIcon: widget.fallbackIcon);
    if (MediaQuery.disableAnimationsOf(context)) return photo;
    return AnimatedBuilder(
      animation: _c,
      builder: (_, child) {
        final t = Curves.easeInOut.transform(_c.value);
        return Transform.scale(scale: 1.08 + 0.1 * t, alignment: Alignment(-0.3 + 0.6 * t, 0), child: child);
      },
      child: photo,
    );
  }
}

/// Apparition douce (fondu + léger glissement), décalée par [index] pour un effet de cascade.
class FadeSlideIn extends StatelessWidget {
  const FadeSlideIn({super.key, required this.child, this.index = 0});
  final Widget child;
  final int index;

  @override
  Widget build(BuildContext context) {
    if (MediaQuery.of(context).disableAnimations) return child;
    return TweenAnimationBuilder<double>(
      tween: Tween(begin: 0, end: 1),
      duration: Duration(milliseconds: 420 + index * 70),
      curve: Curves.easeOutCubic,
      builder: (_, t, c) => Opacity(
        opacity: t.clamp(0, 1),
        child: Transform.translate(
          offset: Offset(0, (1 - t) * 22),
          child: Transform.scale(scale: 0.94 + 0.06 * t, alignment: Alignment.topCenter, child: c),
        ),
      ),
      child: child,
    );
  }
}

/// Ombre douce des cartes (remplace les bordures : rendu plus « produit », moins « gabarit »).
const softShadow = [
  BoxShadow(color: Color(0x14121A35), blurRadius: 18, offset: Offset(0, 8)),
  BoxShadow(color: Color(0x0A121A35), blurRadius: 3, offset: Offset(0, 1)),
];
