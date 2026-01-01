# Changelog

All notable changes to this project will be documented in this file.

## [v2.0.0] - Gheychee Rebranding & Cleanup
**TIMESTAMP**: 2026-01-01 12:30 EST
**VERSION**: v2.0.0

### Added
- **Gheychee Rebranding**: Complete overhaul of project identity from `tg-ytdlp-bot` to `Gheychee`.
  - Updated `README.md` with new branding, links, and assets.
  - Renamed internal services and container names in `docker-compose.yml`.
  - Updated configuration defaults in `CONFIG/config.py`.
  - Updated all internal service references in `services/system_service.py` and `services/lists_service.py`.
- **Changelog**: Established `CHANGELOG.md` for tracking project history.
- **File Headers**: Implemented standardized file headers across core files for better traceability.
- **Localization**: Translated legacy Russian comments to English in core services (`auth_service`, `stats_events`, `system_service`, `lists_service`, `stats_service`, `update_from_repo.py`) along with `auto_translate.py` and `magic.py` to ensure language consistency.

### Changed
- **Update Script**: Updated `update_from_repo.py` to pull from the official `Gheychee` repository (`farjadp/Gheychee`) and `main` branch.
- **Service Management**: `system_service.py` now uses `gheychee-*` service names by default.
- **Lists Service**: `lists_service.py` now checks for `gheychee-bot` container status.

### Fixed
- **Technical Debt**:
  - Removed runtime monkey-patching (`GLOBAL_MESSAGES_PATCH.py`) in favor of proper module architecture in `CONFIG/messages.py`.
  - Applied permanent fixes for `None` comparison errors in 20+ files via `FIX_NONE_COMPARISONS_PATCH.py`.
  - Removed the deprecated `PATCH/` directory.
  - Fixed `magic.py` imports to remove dependencies on deleted patches.

### Security
- **Update Source**: Secured the update mechanism to pull only from the verified `Gheychee` repository.
