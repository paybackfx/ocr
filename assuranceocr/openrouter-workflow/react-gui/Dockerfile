FROM node:20-alpine

WORKDIR /app

# Install dependencies first for better caching
COPY package*.json ./
RUN npm install

# Copy project files
COPY . .

EXPOSE 5173

# Run Vite with explicit host
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
