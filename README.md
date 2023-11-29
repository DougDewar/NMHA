# Network Manager to HTTP Adapter

A simple script which forwards the events sent over Senstar NMS TCP/IP sockets to the http API of Network Optix Witness VMS (or related products).

## Description

The Network Manager to HTTP Adapter takes the messages sent over NMS sockets, attempts to format them to take advantage of Witness' event rules filters, then sends them to Witness using Witness' built-in API. This documentation assumes you are using Witness as the VMS, but it should work for rebranded versions of Witness such as Wisenet Wave or Digital Watchdog Spectrum.

## Getting Started

### Dependencies

* Requires python 3 with the requests library installed.
* Windows 10+

### Setting up

* Visit [python.org](https://www.python.org/) and install the latest version of python 3.
* Open the Windows command prompt and type:
```
pip install requests
```
* Download the script and config files by clicking "<> Code" and then "Download ZIP".
* Extract the ZIP and move the files wherever you would like to run them from.
* Modify the fields in the config.ini file to match your existing setup.

### Executing program

* SETUP NMS EVENTS
* SETUP WITNESS RULES

![](images/NMSAlert1.png)
![](images/WitnessAlert1.png)
![](images/NMSAlert2.png)
![](images/WitnessAlert2.png)

## Authors

Doug Dewar

## Version History

* 0.1
    * Initial Release

## License

This project is licensed under the [NAME HERE] License - see the LICENSE.md file for details