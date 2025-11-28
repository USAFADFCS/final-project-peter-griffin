import os
from fastapi import FastAPI, Form, Request
from fastapi.responses import StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi import BackgroundTasks
from io import BytesIO
from reportlab.pdfgen import canvas
import asyncio
from .run_agents import run_multi_agent_and_get_itinerary  # relative import
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch

app = FastAPI()

# Tell FastAPI where your templates are
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))

# GET endpoint to show HTML form
@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# POST endpoint to handle form submission
@app.post("/plan")
async def plan(
    request: Request,
    origin: str = Form("DEN"),
    destination: str = Form("Rome, Italy"),
    departure_date: str = Form(...),
    nights: int = Form(7),
    budget: str = Form("4000")
):
    user_request = f"I want to leave {origin} and go to {destination} for a week starting {departure_date}. I don't want to spend more than {budget} on flights and hotels."

    try:
        itinerary_text = await asyncio.to_thread(
            run_multi_agent_and_get_itinerary,
            user_request,
            1000  # timeout
        )
    except Exception as e:
        return {"error": str(e)}

    # Generate PDF in memory
    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
    )

    styles = getSampleStyleSheet()
    body = styles["BodyText"]
    body.fontName = "Helvetica"
    body.fontSize = 10
    body.leading = 14  # line spacing

    story = []

    # Convert each line to a Paragraph (auto-wraps)
    for line in itinerary_text.split("\n"):
        if line.strip() == "":
            story.append(Spacer(1, 0.2 * inch))
        else:
            story.append(Paragraph(line, body))

    await asyncio.to_thread(doc.build, story)
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=itinerary.pdf"}
    )