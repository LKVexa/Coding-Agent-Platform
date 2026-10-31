"""Validator for the explicitly used JSON Schema vocabulary, not general JSON Schema."""
import re
import math
from .safety import FoundationError

SUPPORTED = {'$schema', '$id', 'title', 'description', 'type', 'required', 'properties',
             'additionalProperties', 'enum', 'items', 'minItems', 'maxItems',
             'minLength', 'maxLength', 'pattern', 'minimum', 'maximum', 'const'}


def validate(instance, schema, location='$'):
    if isinstance(instance, float) and not math.isfinite(instance):
        raise FoundationError(location + ': non-finite number')
    unsupported = set(schema) - SUPPORTED
    if unsupported:
        raise FoundationError('Unsupported schema vocabulary: ' + ','.join(sorted(unsupported)))
    types = schema.get('type')
    if types:
        if isinstance(types, str):
            types = [types]
        predicates = {'object': lambda x: isinstance(x, dict), 'array': lambda x: isinstance(x, list),
                      'string': lambda x: isinstance(x, str), 'boolean': lambda x: isinstance(x, bool),
                      'null': lambda x: x is None, 'integer': lambda x: isinstance(x, int) and not isinstance(x, bool),
                      'number': lambda x: isinstance(x, (int, float)) and not isinstance(x, bool)}
        if any(t not in predicates for t in types) or not any(predicates[t](instance) for t in types):
            raise FoundationError(location + ': wrong type')
    if 'enum' in schema and instance not in schema['enum']:
        raise FoundationError(location + ': value not permitted')
    if 'const' in schema and instance != schema['const']:
        raise FoundationError(location + ': constant mismatch')
    if isinstance(instance, dict):
        for key in schema.get('required', []):
            if key not in instance:
                raise FoundationError(location + ': missing ' + key)
        props = schema.get('properties', {})
        for key, value in instance.items():
            if key in props:
                validate(value, props[key], location + '.' + key)
            elif schema.get('additionalProperties') is False:
                raise FoundationError(location + ': unexpected ' + key)
    if isinstance(instance, list):
        if len(instance) < schema.get('minItems', 0) or len(instance) > schema.get('maxItems', 10**9):
            raise FoundationError(location + ': array length outside contract')
        if 'items' in schema:
            for i, value in enumerate(instance):
                validate(value, schema['items'], location + '[' + str(i) + ']')
    if isinstance(instance, str):
        if len(instance) < schema.get('minLength', 0) or len(instance) > schema.get('maxLength', 10**9):
            raise FoundationError(location + ': string length outside contract')
        if 'pattern' in schema and re.search(schema['pattern'], instance) is None:
            raise FoundationError(location + ': pattern mismatch')
    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if instance < schema.get('minimum', -float('inf')) or instance > schema.get('maximum', float('inf')):
            raise FoundationError(location + ': number outside contract')

