import hashlib as phash
import decimal
from .crypto_extended import Whirlpool as whirl
from math import floor
from sympy import nextprime
from .bitcoin import hash_encode, int_to_hex, rev_hex

#Set precision to take square roots
decimal.getcontext().prec = 2048

def gHash( header: dict() ) -> int:
    #Get the required data for this block
    hashPrevBlock  = rev_hex(header['prev_block_hash'])
    hashMerkleRoot = rev_hex(header['merkle_root'])
    nNonce   = int_to_hex(header['nonce'], 8)
    nTime    = int_to_hex(int(header['timestamp']), 4)
    nVersion = int_to_hex(header['version'], 4)
    nBits    = int_to_hex(int(header['bits']), 2)


    # Place data as raw bytes into the password and salt for Scrypt:
    # //////////////////////////////////////////////////
    # // pass = hashPrevBlock + hashMerkle + nNonce  //
    # // salt = version       + nBits      + nTime   //
    # /////////////////////////////////////////////////
    passw = hashPrevBlock + hashMerkleRoot + nNonce 
    salt  = nVersion + nBits + nTime

    #Convert to bytes
    passw = bytes.fromhex(passw)
    salt  = bytes.fromhex(salt) 

    # ////////////////////////////////////////////////////////////////////////////////
    # //                                Scrypt parameters                           //
    # ////////////////////////////////////////////////////////////////////////////////
    # //                                                                            //
    # //  N                  = Iterations count (Affects memory and CPU Usage).     //
    # //  r                  = block size ( affects memory and CPU usage).          //
    # //  p                  = Parallelism factor. (Number of threads).             //
    # //  pass               = Input password.                                      //
    # //  salt               = securely-generated random bytes.                     //
    # //  derived-key-length = how many bytes to generate as output. Defaults to 32.//
    # //                                                                            //
    # // For reference, Litecoin has N=1024, r=1, p=1.                              //
    # ////////////////////////////////////////////////////////////////////////////////
    scrypt = phash.scrypt
    N = 1 << 12
    r = 1 << 1
    p = 1
    derived = 0

    #Scrypt Hash to 2048-bits hash.
    #Docs:  hashlib.scrypt(password, *, salt, n, r, p, maxmem=0, dklen=64)
    derived = scrypt( passw, salt=salt, n=N, r=r, p=p, dklen=256)

    #This is a consensus parameter, but it has been 1 and won't change any time soon.
    roundsTotal = 1

    #Prepare GMP objects
    prime_mpz, starting_number_mpz, a_mpz, a_inverse_mpz = 0,0,0,0
        
    for  round in range( roundsTotal): 
        # ///////////////////////////////////////////////////////////////
        # //      Memory Expensive Scrypt: 1MB required.               //
        # ///////////////////////////////////////////////////////////////
        derived = scrypt( derived, salt=salt,n=N, r=r, p=p, dklen=256 )

        # ///////////////////////////////////////////////////////////////
        # //   Add different types of hashes to the core.              //
        # ///////////////////////////////////////////////////////////////
        # //Count the bits in previous hash.
        pcnt_half1 = int(derived[:128].hex(), 16).bit_count()
        pcnt_half2 = int(derived[128:].hex(), 16).bit_count()

        derived_first_half = 0
        derived_second_half = 0

        # //Hash the first 1024-bits of the 2048-bits hash.
        if (pcnt_half1 % 2 == 0): 
            derived_first_half = phash.blake2b( derived[:128] ).digest()
        else:
            derived_first_half = phash.sha3_512( derived[:128] ).digest()

        #Hash the second 1024-bits of the 2048-bits hash.
        if (pcnt_half2 % 2 == 0): 
            derived_second_half = phash.blake2b( derived[128:] ).digest()
        else:
            derived_second_half = phash.sha3_512( derived[128:] ).digest()

        derived = derived_first_half + derived[64:128] + derived_second_half + derived[192:]

        # //////////////////////////////////////////////////////////////
        # // Perform expensive math opertions plus simple hashing     //
        # //////////////////////////////////////////////////////////////
        # //Use the current hash to compute grunt work.
        starting_number_mpz = int.from_bytes(bytes.fromhex( derived.hex() ), byteorder="little")
        a_mpz               = int( floor( decimal.Decimal( starting_number_mpz ).sqrt())) # - \ a = floor( M^(1/2) )
        prime_mpz           = int( floor( decimal.Decimal( a_mpz               ).sqrt())) # - \ p = floor( a^(1/2) )
        prime_mpz           = nextprime( prime_mpz )                      
    
        # //Compute a^(-1) Mod p
        a_inverse_mpz = pow( a_mpz, -1, prime_mpz )
        a_bytes = a_inverse_mpz.to_bytes((a_inverse_mpz.bit_length() + 7) // 8, 'little') 

        # //Xor into current hash digest.
        temp = bytes( int(derived[idx]) ^ int(a_bytes[idx]) for idx in range(len(a_bytes)) )
        derived = temp + derived[len(a_bytes):]

        # //Compute the population count of a_inverse
        irounds = a_inverse_mpz.bit_count() & 0x7f
        
        # //Branch away
        for jj in range(irounds):
            br = ( int.from_bytes( derived, byteorder="little"  ) & 0xffffffffffffffff ).bit_count()

            # //Power mod
            a_inverse_mpz = pow( a_inverse_mpz, irounds, prime_mpz)

            # //Xor data    
            a_bytes = a_inverse_mpz.to_bytes((a_inverse_mpz.bit_length() + 7) // 8, 'little') 
            temp = bytes( int(derived[idx]) ^ int(a_bytes[idx]) for idx in range(len(a_bytes)) )
            derived = temp + derived[len(a_bytes):]

            #Hold data temporarily
            derived_temp = 0

            if (br % 3 == 0):
                derived_temp = phash.sha3_512( derived[:128] ).digest()
                derived = derived_temp + derived[64:] 
            elif (br % 3 == 2):
                derived_temp = phash.blake2b( derived[128:] ).digest()
                derived = derived[:192] + derived_temp 
            else:
                derived_temp = bytes.fromhex( whirl( "".join( [ chr(a) for a in derived ])  ).hexdigest() )
                derived = derived[:112] + derived_temp + derived[176:] 

    w = 0
    w = int.from_bytes( derived, byteorder="little"  )| (1 << (int(header['bits'] - 1) ))
    w = w & ( (1 << int(header['bits'])) - 1 )

    return w


