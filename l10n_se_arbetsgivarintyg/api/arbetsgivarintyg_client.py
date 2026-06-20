# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo SA, Open Source Management Solution, third party addon
#    Copyright (C) 2024- Vertel AB (<https://vertel.se>).
#
##############################################################################

"""
SOAP client for arbetsgivarintyg.nu integration.

Uses the 'zeep' library to communicate with the SOAP web service.

Endpoints:
    Test: https://arbetsgivarintygtest.samorg.org/HR_SystemService/
          ArbetsgivarintygService.svc
    Prod: https://arbetsgivarintyg.nu/HR_SystemService/
          ArbetsgivarintygService.svc

The service exposes a single operation:
    SkickaArbetsgivarintyg(ArbetsgivarintygServiceRequest) →
        ArbetsgivarintygServiceResponse

Response:
    ResultCode (int): 0 = success, non-zero = error
    ResultMessage (str): Description of result

Note: The SOAP service is a WCF (.svc) service from Microsoft BizTalk.
The WSDL is typically available at ?wsdl.
"""

import logging
from datetime import datetime

from odoo import _, fields
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# Try to import zeep, handle gracefully if not installed
try:
    from zeep import Client, Transport
    from zeep.exceptions import Fault, TransportError, ValidationError as ZeepValidationError
    HAS_ZEEP = True
except ImportError:
    _logger.warning(
        'zeep library not installed. Install with: '
        'pip install zeep'
    )
    HAS_ZEEP = False

# Default timeouts (seconds)
DEFAULT_TIMEOUT = 30
DEFAULT_CONNECT_TIMEOUT = 10


class ArbetsgivarintygClient:
    """SOAP client for arbetsgivarintyg.nu."""

    def __init__(self, api_url, api_nyckel, arbetsgivar_id, timeout=None):
        """Initialize the client.

        Args:
            api_url: Full SOAP endpoint URL.
            api_nyckel: Company API key.
            arbetsgivar_id: Company employer ID.
            timeout: Request timeout in seconds.
        """
        if not HAS_ZEEP:
            raise UserError(_(
                'The Python library "zeep" is required for '
                'arbetsgivarintyg.nu integration.\n'
                'Install it with: pip install zeep'
            ))

        self.api_url = api_url
        self.api_nyckel = api_nyckel
        self.arbetsgivar_id = arbetsgivar_id
        self.timeout = timeout or DEFAULT_TIMEOUT

        # Setup zeep transport with timeout
        from requests import Session
        session = Session()
        session.timeout = self.timeout
        self.transport = Transport(session=session, timeout=self.timeout)

        self.client = None

    def _get_wsdl_url(self):
        """Get WSDL URL from the service endpoint."""
        return self.api_url + '?wsdl'

    def _get_client(self):
        """Get or create zeep Client."""
        if self.client is None:
            wsdl_url = self._get_wsdl_url()
            _logger.info('Connecting to WSDL: %s', wsdl_url)
            try:
                self.client = Client(
                    wsdl_url,
                    transport=self.transport,
                )
                _logger.info('WSDL loaded successfully.')
                _logger.debug('Available services: %s',
                              list(self.client.wsdl.services.keys()))
            except TransportError as e:
                _logger.error('Failed to load WSDL: %s', e)
                raise UserError(_(
                    'Could not connect to arbetsgivarintyg.nu.\n'
                    'URL: %(url)s\n'
                    'Error: %(error)s\n\n'
                    'Check that:\n'
                    '- The service is reachable\n'
                    '- API URL is correct\n'
                    '- Your IP is whitelisted (for test environment)',
                    url=self.api_url,
                    error=str(e),
                ))
        return self.client

    def send_certificate(self, request_data):
        """Send an employer certificate to arbetsgivarintyg.nu.

        Args:
            request_data: Dict with the full certificate request structure
                as built by arbetsgivarintyg_mapper.map_intyg_to_request().

        Returns:
            dict: {'result_code': int, 'result_message': str}
        """
        _logger.info(
            'Sending certificate to %s (API key: %s...)',
            self.api_url,
            self.api_nyckel[:8] if self.api_nyckel else 'N/A',
        )

        client = self._get_client()

        try:
            # The operation name from the WCF service
            response = client.service.SkickaArbetsgivarintyg(request_data)

            result_code = response.get('ResultCode', -1)
            result_message = response.get('ResultMessage', '')

            _logger.info(
                'Certificate sent. ResultCode=%s, Message=%s',
                result_code,
                result_message,
            )

            return {
                'result_code': result_code,
                'result_message': result_message,
            }

        except Fault as e:
            _logger.error('SOAP Fault: %s', e)
            return {
                'result_code': -1,
                'result_message': _('SOAP Fault: %s') % str(e),
            }
        except TransportError as e:
            _logger.error('Transport error: %s', e)
            raise UserError(_(
                'Connection to arbetsgivarintyg.nu failed.\n'
                'Error: %(error)s\n\n'
                'Please check your network connection and try again.',
                error=str(e),
            ))
        except ZeepValidationError as e:
            _logger.error('Validation error: %s', e)
            return {
                'result_code': -1,
                'result_message': _('Validation error: %s') % str(e),
            }
        except Exception as e:
            _logger.error('Unexpected error: %s', e, exc_info=True)
            return {
                'result_code': -1,
                'result_message': _('Unexpected error: %s') % str(e),
            }


def send_arbetsgivarintyg(intyg):
    """Convenience function to send an arbetsgivarintyg via the SOAP API.

    Args:
        intyg: l10n_se.arbetsgivarintyg browse record.

    Returns:
        dict: {'result_code': int, 'result_message': str}
    """
    from .arbetsgivarintyg_mapper import map_intyg_to_request

    company = intyg.company_id

    if not company.arbetsgivarintyg_api_nyckel:
        raise UserError(_(
            'API-nyckel saknas för företaget.\n'
            'Gå till Inställningar → Företag → Arbetsgivarintyg och '
            'ange API-nyckel och Arbetsgivar-ID från arbetsgivarintyg.nu.'
        ))
    if not company.arbetsgivarintyg_arbetsgivar_id:
        raise UserError(_(
            'Arbetsgivar-ID saknas för företaget.\n'
            'Gå till Inställningar → Företag → Arbetsgivarintyg och '
            'ange Arbetsgivar-ID från arbetsgivarintyg.nu.'
        ))

    api_url = company.arbetsgivarintyg_api_url

    client = ArbetsgivarintygClient(
        api_url=api_url,
        api_nyckel=company.arbetsgivarintyg_api_nyckel,
        arbetsgivar_id=company.arbetsgivarintyg_arbetsgivar_id,
    )

    request_data = map_intyg_to_request(intyg)
    result = client.send_certificate(request_data)

    # Update the intyg record
    intyg.write({
        'skickat_tidpunkt': fields.Datetime.now(),
        'api_result_code': result['result_code'],
        'api_result_message': result['result_message'],
    })

    if result['result_code'] == 0:
        intyg.state = 'sent'
        intyg.message_post(body=_(
            'Certificate successfully sent to arbetsgivarintyg.nu.\n'
            'Result: %(msg)s',
            msg=result['result_message'],
        ))
    else:
        intyg.state = 'error'
        intyg.message_post(body=_(
            'Failed to send certificate to arbetsgivarintyg.nu.\n'
            'ResultCode: %(code)s\n'
            'Message: %(msg)s',
            code=result['result_code'],
            msg=result['result_message'],
        ))

    return result
