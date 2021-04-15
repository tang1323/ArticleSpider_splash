import six


def bytes_to_str(s, encoding='utf-8'):
    """Returns a str if a bytes object is given."""
    """
    这是为了兼容python2和python3的文件
    unicode编码
    
    """
    if six.PY3 and isinstance(s, bytes):
        return s.decode(encoding)
    return s
