FROM node:18-alpine

WORKDIR /app

COPY package.json ./

RUN npm install


EXPOSE 3000

ENV REACT_APP_N8N_URL=http://n8n:5678

CMD ["npm", "start"]