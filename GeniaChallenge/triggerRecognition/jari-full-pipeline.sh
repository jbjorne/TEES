bash ~/cvs_checkout/GeniaChallenge/triggerRecognition/jari-triggers-for-devel.sh $1 $2

if [ "$1" == "mini" ]; then
	cp /usr/share/biotext/GeniaChallenge/xml/jari-devel-triggers/jari-devel-triggers.xml /usr/share/biotext/GeniaChallenge/xml/jari-devel-triggers-mini.xml
else
	cp /usr/share/biotext/GeniaChallenge/xml/jari-devel-triggers/jari-devel-triggers.xml /usr/share/biotext/GeniaChallenge/xml/jari-devel-triggers.xml
fi

bash ~/cvs_checkout/GeniaChallenge/triggerRecognition/jari-edges-from-predicted-entities.sh $1 $2