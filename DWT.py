def wavelet(data):

    waveletname = 'sym5'

    coeffs = wavedec(data, 'sym5', level=5)

        #cA5,Cd5,cD4,cD5,cD3, cD2, cD1 = coeffs

    cA5,cD5,cD4,cD3,cD2,cD1=coeffs

    A_concate=[cD1,cD2,cD3,cD4,cD5]

    l=A_concate.shape

    print(l)
