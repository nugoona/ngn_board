import datetime

def get_kst_now():
    """ 한국 시간(KST) 반환 """
    return datetime.datetime.utcnow() + datetime.timedelta(hours=9)
