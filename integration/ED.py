from cryptography.fernet import Fernet

class ed:
    def generate_key():
        key = Fernet.generate_key()
        return key

    def encrypt(password, key):
        fernet = Fernet(key)
        encryptedData = fernet.encrypt(password.encode())
        return encryptedData

    def decrypt(encryptedPassword, key):
        fernet = Fernet(key)
        decryptedData = fernet.decrypt(encryptedPassword.decode())
        return decryptedData.decode()



#generate_key()
# - wMaKNv_n0m6CiSyh6G_eQPvmkWSm27qGbBTU9Gx3NT0=

encryptedPass = ed.encrypt("Archer@123","wMaKNv_n0m6CiSyh6G_eQPvmkWSm27qGbBTU9Gx3NT0=")
ed.decrypt(encryptedPass,"wMaKNv_n0m6CiSyh6G_eQPvmkWSm27qGbBTU9Gx3NT0=")
