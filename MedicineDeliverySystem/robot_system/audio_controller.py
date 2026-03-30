from utils.sound import Sound 
import simpleaudio as sa

class AudioController:
    
	#deftes 4 tone variables for the flute to play
	C = Sound(duration=0.5, volume=100, pitch="C4")
	E = Sound(duration=0.5, volume=100, pitch="E4")
	G = Sound(duration=0.5, volume=100, pitch="G4")
	C_12 = Sound(duration=0.5, volume=100, pitch="C5")
	
	def play_delivery_sound(self) -> None:
		C.play()
		G.play()
	
	def play_mission_complete(self) -> None:
		C.play()
		E.play()
		G.play()
		C_12.play()
