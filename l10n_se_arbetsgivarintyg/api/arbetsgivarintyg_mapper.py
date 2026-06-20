# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo SA, Open Source Management Solution, third party addon
#    Copyright (C) 2024- Vertel AB (<https://vertel.se>).
#
##############################################################################

"""
Mapper: Convert Odoo arbetsgivarintyg model to SOAP request dictionary.

The SOAP service expects an ArbetsgivarintygServiceRequest with the following
structure (simplified):

    ArbetsgivarintygServiceRequest
    ├── AGPVersion
    ├── Autentisering
    │   ├── ApiNyckel
    │   ├── ArbetsgivarId
    │   └── SkickatTidpunkt
    ├── Arbetsgivarintyg
    │   ├── ApiCertifikat
    │   │   ├── Arbetsgivare (Adress, Epostadress, Namn, etc.)
    │   │   ├── Avgangsvederlag (IngattAvtal)
    │   │   ├── Anstallning (...)
    │   │   ├── Arbetstagare (...)
    │   │   ├── Arbetstid (...)
    │   │   └── ... (Lon, ArbetadTid, etc.)
    │   └── ...
    └── SoftwareInfo
        ├── Build
        ├── Supplier
        └── Version
"""

import logging
from datetime import datetime

_logger = logging.getLogger(__name__)


def _to_iso_datetime(value):
    """Convert Odoo date/datetime to ISO 8601 string."""
    if not value:
        return None
    if isinstance(value, datetime):
        return value.strftime('%Y-%m-%dT%H:%M:%S')
    return f'{value}T00:00:00'


def _to_decimal(value):
    """Ensure value is float."""
    return float(value) if value else 0.0


def map_intyg_to_request(intyg):
    """Map a l10n_se.arbetsgivarintyg record to a SOAP request dict.

    Args:
        intyg: l10n_se.arbetsgivarintyg browse record.

    Returns:
        dict: Ready for zeep SOAP call.
    """
    company = intyg.company_id

    # Build the full request
    request = {
        'AGPVersion': intyg.agp_version or '1.0',
        'Autentisering': {
            'ApiNyckel': company.arbetsgivarintyg_api_nyckel or '',
            'ArbetsgivarId': company.arbetsgivarintyg_arbetsgivar_id or '',
            'SkickatTidpunkt': _to_iso_datetime(datetime.now()),
        },
        'Arbetsgivarintyg': {
            'ApiCertifikat': {
                'Arbetsgivare': {
                    'Adress': {
                        'CareOf': intyg.ag_co or '',
                        'Ort': intyg.ag_ort or '',
                        'Gatuadress': intyg.ag_gatuadress or '',
                        'Postnummer': intyg.ag_postnummer or '',
                    },
                    'Epostadress': intyg.ag_epost or '',
                    'Namn': intyg.ag_namn or '',
                    'Organisationsnummer': intyg.ag_orgnummer or '',
                    'Telefonnummer': intyg.ag_telefon or '',
                    'Samtycke': intyg.samtycke,
                    'AnvandRedanRegistreradInformation': intyg.anvand_registrerad_info,
                },
                'Avgangsvederlag': {
                    'IngattAvtal': intyg.avgangsvederlag_avtal,
                },
                'Anstallning': {
                    'Befattning': intyg.befattning or '',
                    'ArbetstidOmfattning': _to_decimal(intyg.arbetstid_procent),
                    'AnstallningstidPeriod': {
                        'Start': _to_iso_datetime(intyg.anstallning_start),
                        'Slut': _to_iso_datetime(
                            intyg.anstallning_slut
                            if not intyg.fortfarande_anstalld
                            else None
                        ),
                    },
                    'Tjanstledig': intyg.tjanstledig,
                    'Tjanstledigheter': [
                        {
                            'Tjanstledighet': {
                                'OmfattningProcent': tl.omfattning_procent or 0,
                                'Period': {
                                    'Start': _to_iso_datetime(tl.start),
                                    'Slut': _to_iso_datetime(tl.slut),
                                },
                                'Orsak': tl.orsak or '',
                            }
                        }
                        for tl in intyg.tjanstledighet_ids
                    ],
                    'FortfarandeAnstalld': intyg.fortfarande_anstalld,
                    'Anstallningsform': {
                        'TidsbegransadAnstallningSlutdatum': _to_iso_datetime(
                            intyg.tidsbegransad_slut
                        ),
                        'ProvanstallningSlutdatum': _to_iso_datetime(
                            intyg.provanstallning_slut
                        ),
                        'Typ': intyg.anstallningsform,
                    },
                    'OvrigUpplysning': {
                        'OvrigUpplysning': intyg.ovrig_upplysning or '',
                    },
                    'ErbjudandeOmFortsattArbete': {
                        'DatumAvbojtErbjudande': _to_iso_datetime(
                            intyg.erbjudande_avbojt_datum
                        ),
                        'TimmarPerVeckaHeltid': _to_decimal(
                            intyg.erbjudande_heltid_tim
                        ),
                        'AccepteratErbjudande': intyg.erbjudande_accepterat,
                        'TillsvidareAnstallning': intyg.erbjudande_tillsvidare,
                        'FinnsErbjudande': intyg.erbjudande_finns,
                        'FinnsErbjudandeOmfattning': {
                            'Start': _to_iso_datetime(intyg.erbjudande_start),
                            'Slut': _to_iso_datetime(intyg.erbjudande_slut),
                        },
                        'TimmarPerVeckaDeltid': _to_decimal(
                            intyg.erbjudande_deltid_tim
                        ),
                        'ProcentAvHeltid': _to_decimal(
                            intyg.erbjudande_procent
                        ),
                        'Arbetstid': intyg.erbjudande_arbetstid or 'Ingen',
                    },
                    'Upphorandeorsak': {
                        'Orsak': intyg.upphorandeorsak,
                        'AnnanOrsak': intyg.annan_orsak_text or '',
                        'Beskedsdatum': _to_iso_datetime(intyg.beskedsdatum),
                        'TidsbegransadAnstallningDatumBesked': _to_iso_datetime(
                            intyg.tidsbegransad_besked
                        ),
                    },
                    'Lon': {
                        'Belopp': _to_decimal(intyg.lon_belopp),
                        'AndraLonetillaggLista': [
                            {
                                'AndraLonetillaggRad': {
                                    'Belopp': _to_decimal(lt.belopp),
                                    'Dagar': _to_decimal(lt.dagar),
                                    'Beskrivning': lt.beskrivning or '',
                                    'Timmar': _to_decimal(lt.timmar),
                                    'Manad': lt.manad,
                                    'Lonetillaggstyp': lt.lonetillaggstyp,
                                    'Ar': lt.ar,
                                }
                            }
                            for lt in intyg.lonetillagg_ids
                        ],
                        'ExtraLon': intyg.lon_extra,
                        'VarierandeTimlon': intyg.lon_varierande_timlon,
                        'Mertidstillagg': _to_decimal(intyg.lon_mertid),
                        'Overtidstillagg': _to_decimal(intyg.lon_overtid),
                        'TypAvLon': intyg.lon_typ,
                        'Ar': intyg.lon_ar or datetime.now().year,
                    },
                    'SpeciellAnstallningsinformation': {
                        'AnstalldBemanning': intyg.anstalld_bemanning,
                        'Skiftarbete': intyg.skiftarbete,
                    },
                    'Lararlon': {
                        'Uppehallslon': intyg.uppehallslon,
                        'UppehallslonBelopp': _to_decimal(
                            intyg.uppehallslon_belopp
                        ),
                        'Ferielon': intyg.ferielon,
                        'FerielonBelopp': _to_decimal(intyg.ferielon_belopp),
                        'FerielonDagar': intyg.ferielon_dagar or 0,
                        'SemesterDatumOmfattning': {
                            'Start': _to_iso_datetime(intyg.semester_start),
                            'Slut': _to_iso_datetime(intyg.semester_slut),
                        },
                    },
                    'ArbetadTid': {
                        'Undervisningstimmar': _to_decimal(
                            intyg.undervisningstimmar
                        ),
                        'ArbetadTidDatumOmfattning': {
                            'Start': _to_iso_datetime(intyg.arbetad_tid_start),
                            'Slut': _to_iso_datetime(intyg.arbetad_tid_slut),
                        },
                        'Undervisningstid': intyg.undervisningstid,
                        'ArbetadTidManader': [
                            {
                                'ArbetadTidManad': {
                                    'Franvaro': _to_decimal(at.franvaro),
                                    'Manad': at.manad,
                                    'Mertid': _to_decimal(at.mertid),
                                    'Overtid': _to_decimal(at.overtid),
                                    'ArbetadeTimmar': _to_decimal(
                                        at.arbetade_timmar
                                    ),
                                    'Ar': at.ar,
                                }
                            }
                            for at in intyg.arbetad_tid_ids
                        ],
                    },
                    'Arbetstagare': {
                        'Epostadress': intyg.at_epost or '',
                        'Fornamn': intyg.at_fornamn or '',
                        'Efternamn': intyg.at_efternamn or '',
                        'Telefonnummer': intyg.at_telefon or '',
                        'SkickaSMS': intyg.at_skicka_sms,
                        'Personnummer': intyg.at_personnummer or '',
                    },
                    'Arbetstid': {
                        'ArbetstidHeltidTimmar': _to_decimal(
                            intyg.arbetstid_heltid_tim
                        ),
                        'ProcentAvHeltid': _to_decimal(intyg.arbetstid_procent),
                        'ArbetstidDeltidTimmar': _to_decimal(
                            intyg.arbetstid_deltid_tim
                        ),
                        'Typ': intyg.arbetstid_typ,
                    },
                },
            },
        },
        'SoftwareInfo': {
            'Build': intyg.software_build or '',
            'Supplier': intyg.software_supplier or 'Vertel AB',
            'Version': intyg.software_version or '1.0',
        },
    }

    return request
