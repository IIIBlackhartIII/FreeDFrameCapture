import socket
import numpy as np
import time

###########################
### FreeD Specification ###
###########################
class FreeD:
    def __init__ (self,pitch: np.float32(),yaw: np.float32(),roll: np.float32(),posz: np.float32(),posx: np.float32(),posy: np.float32(),zoom: int(),focus: int()):
        self.pitch = pitch
        self.yaw = yaw
        self.roll = roll
        self.posz = posz
        self.posx = posx
        self.posy = posy
        self.zoom = zoom
        self.focus = focus
        
    def returnData (self):
        #human readable string of object's data
        return f"{self.pitch},{self.yaw},{self.roll},{self.posz},{self.posx},{self.posy},{self.zoom},{self.focus}"
    
    def checksum (data: bytearray()):
        sum = int(64)
        for i in range(0,28,1):
            byte = data[i]
            sum = sum - int(byte)
        sum_mod = sum % 256
        return sum_mod
    
    def decode (data: bytearray()):
        if FreeD.checksum(data) == int(data[28]):
            #init FreeD data object        
            tracking_data = FreeD(0,0,0,0,0,0,0,0)
            
            #get tracking data from packet bytes
            tracking_data.pitch = FreeD.getRotation(data[2:5])
            tracking_data.yaw = FreeD.getRotation(data[5:8])
            tracking_data.roll = FreeD.getRotation(data[8:11])
            tracking_data.posz = FreeD.getPosition(data[11:14])
            tracking_data.posx = FreeD.getPosition(data[14:17])
            tracking_data.posy = FreeD.getPosition(data[17:20])
            tracking_data.zoom = FreeD.getEncoder(data[20:23])
            tracking_data.focus = FreeD.getEncoder(data[23:26])
            
            #return FreeD data object
            return tracking_data
        else:
            print("Checksum doesn't match, probably not FreeD data")
            
    def getRotation (data : bytearray()) -> np.float32():
        return np.float32(np.int32(data[0]<<24)|np.int32(data[1]<<16)|np.int32(data[2])<<8) / 32768 / 256
    
    def getPosition (data : bytearray()) -> np.float32():
        return np.float32(np.int32(data[0]<<24)|np.int32(data[1]<<16)|np.int32(data[2])<<8) / 64 / 256
    
    def getEncoder (data : bytearray()) -> int():
        value = bytearray([0x00])
        value.extend(data)
        return int.from_bytes(value, byteorder='big')
        # TODO - figure out why the getEncoder method isn't returning correct values
        

#################
### UDP Setup ###
#################
UDP_IP = "0.0.0.0"  # Listen on all available network interfaces
UDP_RECEIVE_PORT = 6301  # Choose a port number
UDP_SEND_PORT = 6321 # Choose a port number
SEND_IP = "127.0.0.1" 

# create Udp Packet struct that abstracts bytes() in order to make a list of incoming packets
class UdpPacket:
    def __init__(self,packet : bytes()):
        self.packet = packet
    
    def get_packet(self):
        return self.packet

#global func for sending packets
def rebroadcastPacket (buffer : [], send_socket : socket.socket(), send_address):
    packet_to_send = UdpPacket.get_packet(buffer[0])
    send_socket.sendto(packet_to_send, send_address) # send first packet
    del buffer[0] # remove first packet 
    return buffer

# Create a UDP socket
server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Bind the socket to the IP address and port
receive_address = (UDP_IP, UDP_RECEIVE_PORT)
server.bind(receive_address)
send_address = (SEND_IP, UDP_SEND_PORT)

print(f"Listening on {UDP_IP}:{UDP_RECEIVE_PORT}")

# Packet Buffer Init
packet_buffer = [] # list of received packets
frames_to_buffer = 8 # how many packets to buffer before starting to send
frame_rate = 24 # frame rate to rebroacast the packets
frame_delay = 1 / frame_rate # how many ms makes up our frame rate (for delaying packets)
send_time = time.time() # init variable for measuring time between packets

#################
### MAIN LOOP ###
#################
while True:
    # Receive data
    data, address = server.recvfrom(1024)  # default buffer size 1024 bytes

    # Process the received packet
    data_packet = np.frombuffer(data, dtype=np.uint8)
    decoded_data = FreeD.decode(data_packet)
    if (decoded_data != None):
        print(f"Recieved FreeD Packet: {decoded_data.returnData()}")
        
    # Buffer packets and rebroadcast on another port with consistent timing
    current_packet = UdpPacket(data)
    packet_buffer.append(current_packet)
    
    if (len(packet_buffer) >= frames_to_buffer):
        time_since_sent = time.time() - send_time
        if (time_since_sent >= frame_delay):
            packet_buffer = rebroadcastPacket(packet_buffer, client, send_address) # rebroadcast packet and update buffer
            print (f"Send Packet to port {UDP_SEND_PORT}")