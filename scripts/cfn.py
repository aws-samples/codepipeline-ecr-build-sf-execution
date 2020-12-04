#'Update or create a stack given a name and template + params'
from __future__ import division, print_function, unicode_literals

import os
from datetime import datetime
import logging
import json
import sys
import itertools, functools
import boto3
import botocore


cf = boto3.client('cloudformation',region_name='us-east-1')  # pylint: disable=C0103
log = logging.getLogger('deploy.cf.create_or_update')  # pylint: disable=C0103


def boto_all(func, *args, **kwargs):
    """
    Iterate through all boto next_token's
    """

    ret = [func(*args, **kwargs)]

    while ret[-1].next_token:
        kwargs['next_token'] = ret[-1].next_token
        ret.append(func(*args, **kwargs))

    # flatten it by 1 level
    return list(functools.reduce(itertools.chain, ret))

class Cloudformation(object):
    # this is from http://docs.aws.amazon.com/AWSCloudFormation/latest/APIReference/API_Stack.html
    # boto.cloudformation.stack.StackEvent.valid_states doesn't have the full list.
    VALID_STACK_STATUSES = ['CREATE_IN_PROGRESS', 'CREATE_FAILED', 'CREATE_COMPLETE', 'ROLLBACK_IN_PROGRESS',
                            'ROLLBACK_FAILED', 'ROLLBACK_COMPLETE', 'DELETE_IN_PROGRESS', 'DELETE_FAILED',
                            'DELETE_COMPLETE', 'UPDATE_IN_PROGRESS', 'UPDATE_COMPLETE_CLEANUP_IN_PROGRESS',
                            'UPDATE_COMPLETE', 'UPDATE_ROLLBACK_IN_PROGRESS', 'UPDATE_ROLLBACK_FAILED',
                            'UPDATE_ROLLBACK_COMPLETE_CLEANUP_IN_PROGRESS', 'UPDATE_ROLLBACK_COMPLETE']

    default_region = 'us-east-1'

    def __init__(self, region=None):
        """
        :param region: AWS region
        :type region: str
        """

        self.connection = cf

        if not self.connection:
            raise

    def tail_stack_events(self, name, initial_entry=None):
        """
        This function is a wrapper around _tail_stack_events(), because a generator function doesn't run any code
        before the first iterator item is accessed (aka .next() is called).
        This function can be called without an `inital_entry` and tail the stack events from the bottom.

        Each iteration returns either:
        1. StackFailStatus object which indicates the stack creation/update failed (last iteration)
        2. StackSuccessStatus object which indicates the stack creation/update succeeded (last iteration)
        3. dictionary describing the stack event, containing the following keys: resource_type, logical_resource_id,
           physical_resource_id, resource_status, resource_status_reason

        A common usage pattern would be to call tail_stack_events('stack') prior to running update_stack() on it,
        thus creating the iterator prior to the actual beginning of the update. Then, after initiating the update
        process, for loop through the iterator receiving the generated events and status updates.

        :param name: stack name
        :type name: str
        :param initial_entry: where to start tailing from. None means to start from the last item (exclusive)
        :type initial_entry: None or int
        :return: generator object yielding stack events
        :rtype: generator
        """

        if initial_entry is None:
            return self._tail_stack_events(name, len(self.describe_stack_events(name)))
        elif initial_entry < 0:
            return self._tail_stack_events(name, len(self.describe_stack_events(name)) + initial_entry)
        else:
            return self._tail_stack_events(name, initial_entry)

    def describe_stack_events(self, name):
        """
    Describe CFN stack events

    :param name: stack name
    :type name: str
    :return: stack events
    :rtype: list of boto.cloudformation.stack.StackEvent
    """

        return boto_all(self.connection.describe_stack_events,StackName=name)

    def _tail_stack_events(self, name, initial_entry):
        """
        See tail_stack_events()
        """

        previous_stack_events = initial_entry

        while True:
            stack = self.describe_stack(name)
            stack_events = self.describe_stack_events(name)

            if len(stack_events) > previous_stack_events:
                # iterate on all new events, at reversed order (the list is sorted from newest to oldest)
                for event in stack_events[:-previous_stack_events or None][::-1]:
                    yield {'resource_type': event.resource_type,
                           'logical_resource_id': event.logical_resource_id,
                           'physical_resource_id': event.physical_resource_id,
                           'resource_status': event.resource_status,
                           'resource_status_reason': event.resource_status_reason,
                           'timestamp': event.timestamp}

                previous_stack_events = len(stack_events)

            if stack.stack_status.endswith('_FAILED') or \
                    stack.stack_status in ('ROLLBACK_COMPLETE', 'UPDATE_ROLLBACK_COMPLETE'):
                yield StackFailStatus(stack.stack_status)
                break
            elif stack.stack_status.endswith('_COMPLETE'):
                yield StackSuccessStatus(stack.stack_status)
                break

            time.sleep(2)
    
class StackFailStatus():
    pass
class StackSuccessStatus():
    pass




def main(stack_name, template, parameters):
    'Update or create stack'
    template_data = _parse_template(template)
    parameter_data = _parse_parameters(parameters)

    params = {
        'StackName': stack_name,
        'TemplateBody': template_data,
        'Parameters': parameter_data,
        'Capabilities':['CAPABILITY_NAMED_IAM','CAPABILITY_AUTO_EXPAND'],
        # 'DisableRollback': True
    }

    try:
        if _stack_exists(stack_name):
            print('Updating {}'.format(stack_name))
            stack_result = cf.update_stack(**params)
            waiter = cf.get_waiter('stack_update_complete')

            # cfn = Cloudformation()
            # cfn.tail_stack_events(stack_name)
        else:
            params.update(DisableRollback = True)
            print('Creating {}'.format(stack_name))
            stack_result = cf.create_stack(**params)
            waiter = cf.get_waiter('stack_create_complete')
        print("...waiting for stack to be ready...")
        waiter.wait(StackName=stack_name)
    except botocore.exceptions.ClientError as ex:
        error_message = ex.response['Error']['Message']
        if error_message == 'No updates are to be performed.':
            print("No changes")
        else:
            raise
    else:
        print(json.dumps(
            cf.describe_stacks(StackName=stack_result['StackId']),
            indent=2,
            default=json_serial
        ))


def _parse_template(template):
    with open(template) as template_fileobj:
        template_data = template_fileobj.read()
    cf.validate_template(TemplateBody=template_data)
    return template_data


def _parse_parameters(parameters):
    with open(parameters) as parameter_fileobj:
        parameter_data = json.load(parameter_fileobj)
        # update parameters with environment variables
        for i in parameter_data:
            if i['ParameterKey'] in os.environ:
                i['ParameterValue'] = os.environ[i['ParameterKey']]
                print('Updated {} parameter from environment variables.'.format(i['ParameterKey']))

    return parameter_data


def _stack_exists(stack_name):
    stacks = cf.list_stacks()['StackSummaries']
    for stack in stacks:
        if stack['StackStatus'] == 'DELETE_COMPLETE':
            continue
        if stack_name == stack['StackName']:
            return True
    return False


def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, datetime):
        serial = obj.isoformat()
        return serial
    raise TypeError("Type not serializable")


if __name__ == '__main__':
    main(*sys.argv[1:])