' Create the shell object
	Set objShell = CreateObject("WScript.Shell")
	amibrokerExe = "Broker.exe"
	folderAmi = objShell.Environment("SYSTEM")("AmibrokerBatch")
	abbFile = folderAmi & "ALL_Shares.abb"
	commandAmi= """" & amibrokerExe & """ /runbatch """ & abbFile & """ /exit"

' Execute the command
	objShell.Run commandAmi, 1, True
	
