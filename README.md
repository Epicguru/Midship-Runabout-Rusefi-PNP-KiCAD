### Original Repo:
https://github.com/threepotMR2/Midship-Runabout-Rusefi-PNP-pcb

## MRR Epicguru Fork
This is a WIP KiCAD version of @threepotMR2 's Midship Runabout Rusefi project, which aims to be an affordable Plug & Play programmable ECU for the 1ZZFE or 2ZZ MR2 Spyder.  

Compared to the original, this has been done in [KiCAD 10](https://www.kicad.org/), which is free open source schematic and PCB design software. If you also use the [JLCPCB Tools plugin](https://github.com/bouni/kicad-jlcpcb-tools) then you will get all parts ready to send for manufacturing with JLCPCB in one click (though pay attention to the rotation of components! I have not yet done the rotation corrections in the project, so you will need to do it when you upload the production files!).  

<p align="center">
  <img src="Readme%20Images/image.png" alt="alt text" width="49%">
  <img src="Readme%20Images/image-2.png" alt="alt text" width="49%">
  <br>
  <img src="Readme%20Images/image-7.png" alt="alt text" width="49%">
  <img src="Readme%20Images/image-8.png" alt="alt text" width="49%">
</p>

## Changes compared to original

### Important
- It is now a 4-layer board with signal on the front and back and two inner ground layers. This should improve signal integrity and reduce noise, especially under the VR circuits and the new 3.3v buck converter. This only adds around 1.5 EUR per board.
- Added TVS protection diodes  to the high and low-side relay switches. I haven't been able to verify whether the car's relays have built-in diodes (if they do they don't show up on wiring diagrams), but if they don't then each time they are switched then the coils will shove huge voltage spikes through the PhotoMOS which will kill them over time. If they do have built-in diodes, adding these extra ones doesn't hurt.
- Changed PhotoMOS fuses: the original fuses were 1A fast-blow fuses. The PhotoMOS are rated for 0.55A continuous. I have replaced the fuses with 0.5A hold, 1A trip resettable PTCs. It means that they still protect against short-circuits, but don't need replacing in that event.
- Replaced various resistors that were out-of-spec:
  - **R24**: This resistor was a 330 Ohm 0603 part that was limiting current to the PhotoMOS. The resistance was fine, allowing around 40mA through the LED vs 50mA max spec, but at that current it was dissipating around 0.5W of heat which is well above the 0.1W it is rated for. The resistor would cook over time, especially in a sealed case. It failing would turn the main relay off which could range from very annoying to really dangerous.
  - **R22**: This is the BEAN pull-up resistor. Resistance is fine but again it burns too much power: 0.2W in a 0.1W spec part. Changed to a larger package rated for 0.5W, same resistance.
  - **R15**: Tach output resistor. Did not really need changing but it was swapped for a higher power anti-surge resistor that just means that if you accidentally short the tach output (such as touching tach to chassis when removing dash) it won't burn the resistor out.
- Changed 12V input surge clamp to 18V, 600W part to protect U10 (buck converter) and U14 (tach output opto). The original 15V standoff was a little too close to normal charging voltage for my liking, increasing to 18 won't hurt anything on the circuit. I still need to improve this protection, but it should be fine for now.

### Other fixes & changes
- Fixed A/C pressure switch hardware: the manual says that you will get between 9V and 14V when pressure is good, and '-' when the pressure is bad. I haven't been able to figure out if that means LOW or just floating, but it's a problem either way.   
The problem with the original circuitry is that it relied on the voltage difference between the switch and VIN. If VIN happens to be too close to the P/S voltage, then the LED will not turn on. That leaves GPIO21 floating. Because there is no pull-up/down enabled in the firmware, I suspect that it was simply drifting HIGH which is why it was still working.  
More concerning is that if there is a fault: if the switch goes LOW then all of VIN is going to go through the LED, which puts R13 out-of-spec (~0.2W rated at 0.1W), and it will also still read as 'OK' on the ESP32. If the switch goes floating then we are back to the floating GPIO21 scenario, where it will probably still drift high.
  - I've fixed this by shuffling things around so that the A/C switch is now the LED driver. If it goes LOW or floating, then the LED turns off. If the LED turns off then there is an additional pull-down resistor on the output to make sure that it is low without having to rely on firmware pull-down.  
  <img src="Readme%20Images/image-3.png" alt="alt text" width="50%">  
- Swapped 3.3v LDO for an automotive-grade buck converter. The LDO is fine for tiny currents but as current increases it starts to burn lots of power.
  - On the original board it was around 1.4W of heat produced, including the optocouplers. If you want to connect to the ESP32 Wifi then it could increase up to around 1.7W, which will get very toasty in an enclosed case. On the original board there is also a mistake that makes this worse, the large tab is not connected to the ground plane. The large tab is supposed to act as a heat sink by putting heat into the copper. It is not connected and so it will get even hotter. The LM2937 has a thermal-shutdown of 150C which isn't hard to reach without a heatsink and that much current. It's probably fine with the ESP32 WiFi turned off and a heat sink on it.  

  <img src="Readme%20Images/image-1.png" alt="Gap" width="33%">  

  - The buck converter is a lot more efficient and costs almost exactly the same. The only disadvantage is that it can't handle huge input voltage spikes, see notes above.
- Populated all spare connections on the 'magic 5th connector'. There are now:
  - 4 analogue inputs (one has a 500k pull-down).
  - 1 digital input with a 10k pull-up.
- Added 1-pin male headers to the missing slots on the board.
- All male headers are now gold-plated and rated for 3A each. This should allow using female headers soldered on to the uaEFI to allow you to swap between daughter-boards without desoldering the RUS. Needs testing, might be too tall for the stock ECU case.
- Almost all power traces have been beefed up, especially the 12V input. 12V in can carry up to 4A if you are using the onboard wideband controller, so I've erred on the side of caution.
- Improved clearance around the crank and cam VR traces and do not route them through vias: these are very high voltage and noisy, so they have been kept on the top layer and away from other inputs as much as possible.

### Minor changes
- Added a jumper for the CAN bus termination resistor. If you have an external dash or logging device that has one soldered in, you can just remove the jumper rather than having to de-solder it.
- Added a mirrored set of female headers for the ESP32. That just makes probing easier, and lets you quite easily bodge in new circuitry. It may make it so that you have to use a 90-degree USB connector on the RUS since there is less space now.
- Added missing second ESP32 GND connection
- Added several test-points.

## Doubts
- The original board the stock OX1A pin was tied to signal ground. I'm not sure if that is a mistake or if Threepot was using the stock sensor plug for something else. I've added a jumper to either keep it tied to signal ground or just leave it floating. If the user wants to keep the stock sensor plugged in, for some reason, then the jumper should not be used.
- The original schematic and gerber/BOM files are slightly out-of-sync and the most significant change seems to be the VR conditioning capacitors. I haven't spent enough time researching these VR chips to know what the correct values are, so I've trusted what the JLCPCB BOM part number says and used those capacitor values.

## Does it work?
No clue, I've ordered one to try.  
I'll update the repo once I have had a chance to test it.

## Can it run the stock car?
No, you need an external wideband sensor in the exhaust, and the stock narrowband sensors need to be removed or they will be destroyed.

## How much does it cost?
You have to source the connector which can be had for around 25$ straight from the supplier, or 45$ from the RusEFI ebay shop.  
You also need the 17 pin 5th connector which is just a few dollars from China.
The board itself, with the components specified, costs around 70-100$ from JLCPCB. If you order many of them, the cost will be closer to 60$ per assembled board. If you order just two (minimum amount), expect around 100$ per board.  
The RusEFI uaEFI is around 150$.  

Overall, including the rusEFI & connectors, shipping, import duties and taxes, it cost me around 250 EUR per ECU when building two of them.

## Future plans/work
- [ ] Improve power input protections, including constant reverse polarity protection.
- [ ] Add ESD protection to 5th connector pins.
- [ ] Add ADC chip(s) and screw terminals. Using LUA scripting, you can effectively get 2 more 'free' analogue inputs to the ECU which can be used for anything, and you can get up to 6 additional analogue inputs that can be used for just logging.  
But, you can also use any number of inputs to be applied directly to the tune, or used to replace un-populated physical pins. That can be used to do two interesting things:
   - Create custom buttons/switches that do things like toggle launch control, boost control etc. without having to use any of the ECU's limited physical/virtual inputs.
   - Effectively allows you to 're-wire' unused physical pins without having to actually solder anything on the RUS.


## Are these available/for sale?
Keeping with the spirit of @threepotMR2 's MRR project, this version is open source. You can download all the files needed to have this manufactured, and you can buy a rusEFI uaEFI. If you know how to solder and have ~300$ to burn, you can get everything you need.  

I would like to eventually sell a complete assembled kit, including a 3D printed case, MAP air input, USB port etc. completely ready for use without having to touch the original ECU. I also have a gauge pod project, intended for MR2 turbo cars, that works with this ECU, which I would like to publish and maybe sell.  

ThreepotMR2 plans on selling his design as a kit, so that will be the place to buy one especially if you live in the UK. Since this is 99% his design, work and months testing I will not be selling these directly in the foreseeable future.  

In the future, if he isn't bothered by it, I might still turn these into a product that I sell directly which I'm sure people in Europe would appreciate: shipping and import duty costs are half of the price for most of these components and boards, so extra inter-continental fees really hurt.

![alt text](Readme%20Images/image-6.png)
![alt text](Readme%20Images/image-5.png)
![alt text](Readme%20Images/image-4.png)