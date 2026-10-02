FROM maven:3.9-eclipse-temurin-21 AS b
WORKDIR /w
COPY pom.xml .
COPY src src
RUN mvn -q -DskipTests package
FROM eclipse-temurin:21-jre
COPY --from=b /w/target/medisave-backend-1.0.0.jar /app.jar
CMD ["sh","-c","java -Dserver.port=${PORT:-8080} -jar /app.jar"]
