import urllib
import urllib2

class PardotException(Exception):
    pass


def post_to_pardot(form_data, url):
    data = urllib.urlencode(form_data)
    req = urllib2.Request(url, data)
    response = urllib2.urlopen(req)
    the_page = response.read()
    if the_page.find('Cannot find error page') == -1:
        message = {
            'status':'success',
        }
    else:
        message = {
            'status':'failure',
            'errors': the_page.split('~~~')
        }
        list =[]
        for error in message.get('errors'):
            if error.find('-') == -1:
                list.append(error)
        for error in list:
            message.get('errors').remove(error)
    if message['status'] == 'failure':
        raise PardotException(message['errors'])
    return message



