# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from . import aap_currency_base as currency_base
from copy import deepcopy


def get_rate():
    """Get GBP to AUD rate."""
    try:
        return currency_base.get_rate('GBP', 'AUD')
    except:
        raise LookupError('Failed to retrieve currency conversion rate')


def gbp_to_aud(item, **kwargs):
    """Convert AUD to GBP."""

    rate = get_rate()

    # matches Symbol-Value-Suffix pattern i.e. GBP 52 mln
    symbol_first_regex = r'([£]|(GBP)|(STG))\s*\-?\s*\(?(((\d{1,}((\,\d{3})*|\d*))?' \
                         r'(\.\d{1,4})?)|((\d{1,}((\,\d{3})*|\d*))(\.\d{0,4})?))\)?' \
                         + currency_base.SUFFIX_REGEX

    # matches Value-Suffix-Symbol pattern i.e. 52 mln GBP
    symbol_last_regex = r'\(?(((\d{1,}((\,\d{3})*|\d*))?(\.\d{1,4})?)((\d{1,}((\,\d{3})*|\d*))(\.\d{0,4})?))' \
                        + currency_base.SECONDARY_SUFFIX_REGEX \
                        + '\s?([£]|(GBP)|(STG)|([p|P]ounds?))'

    symbol_first_result = currency_base.do_conversion(deepcopy(item),
                                                      rate,
                                                      '$A',
                                                      symbol_first_regex,
                                                      match_index=0,
                                                      value_index=4,
                                                      suffix_index=17)

    symbol_last_result = currency_base.do_conversion(deepcopy(item),
                                                     rate,
                                                     '$A',
                                                     symbol_last_regex,
                                                     match_index=0,
                                                     value_index=1,
                                                     suffix_index=13)

    symbol_first_result[1].update(symbol_last_result[1])

    return symbol_first_result


name = 'gbp_to_aud'
label = 'Currency GBP to AUD'
callback = gbp_to_aud
access_type = 'frontend'
action_type = 'interactive'
group = 'currency'
