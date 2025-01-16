from netml.pparser.parser import PCAP

pcap = PCAP('packet_capture/flood_con:10-14_time:20_decrypted.pcap')

pcap.pcap2pandas()

pdf = pcap.df