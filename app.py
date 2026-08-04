import html

import gradio as gr

import styles
from travel_app import Travel_App


LAUNCH_STYLE = {
    "theme": styles.THEME,
    "css": styles.CSS,
    "head": styles.JS,
}


HEADER = """
<div id="header">
    <div class="context-label">Your personal AI travel planner</div>
    <h1>Travel Agent</h1>
    <div class="brand-bar"></div>
</div>
"""


def render_todos(todos):
    """Render the agent's TodoListMiddleware todos in the plan panel."""

    if not todos:
        items = """
        <div class="placeholder">
            Your travel agent will write its plan here as it works
        </div>
        """
    else:
        items = "<ul>" + "".join(
            f'''
            <li class="{todo["status"]}">
                <span class="mark"></span>
                {html.escape(todo["content"])}
            </li>
            '''
            for todo in todos
        ) + "</ul>"

    return f"<h3>Travel Plan</h3>{items}"


async def setup():
    """Create and initialise the Travel Agent when the UI loads."""

    travel_agent = Travel_App()

    await travel_agent.setup()

    return travel_agent, gr.update(interactive=True)


async def process_message(
    travel_agent,
    message,
    success_criteria,
    history,
):
    """Send a new request to the Travel Agent."""

    if travel_agent is None:
        # MCP servers / agent have not finished starting yet
        return history, gr.update(visible=False), travel_agent

    if not message.strip():
        return history, gr.update(visible=False), travel_agent

    results = await travel_agent.run_turn(
        message,
        success_criteria,
        history,
    )

    return (
        results,
        gr.update(visible=travel_agent.paused),
        travel_agent,
    )


async def approve(travel_agent, history):
    """Approve a HumanInTheLoopMiddleware action."""

    if travel_agent is None:
        return history, gr.update(visible=False), travel_agent

    results = await travel_agent.resume(history)

    return (
        results,
        gr.update(visible=travel_agent.paused),
        travel_agent,
    )


def watch_todos(travel_agent):
    """Update the live TodoListMiddleware plan every second."""

    if travel_agent:
        return render_todos(travel_agent.todos)

    return render_todos([])


async def reset(travel_agent):
    """Destroy the old agent and start a fresh travel session."""

    if travel_agent:
        travel_agent.cleanup()

    new_travel_agent = Travel_App()

    await new_travel_agent.setup()

    return (
        "",                             # message
        "",                             # success criteria
        [],                             # chatbot
        gr.update(visible=False),       # approve button
        new_travel_agent,               # state
    )


def free_resources(travel_agent):
    """Clean up MCP servers when the Gradio state is deleted."""

    if travel_agent:
        travel_agent.cleanup()


# -------------------------------------------------------------------
# UI
# -------------------------------------------------------------------

with gr.Blocks(title="AI Travel Agent") as ui:

    gr.HTML(HEADER)

    # Stores the Travel_App object for this Gradio session
    travel_agent = gr.State(
        delete_callback=free_resources
    )

    # ---------------------------------------------------------------
    # Main display
    # ---------------------------------------------------------------

    with gr.Row():

        chatbot = gr.Chatbot(
            label="Travel Agent",
            height=420,
            scale=3,
            elem_id="chat",
        )

        with gr.Column(scale=1):

            todos_panel = gr.HTML(
                render_todos([]),
                elem_id="plan-panel",
            )

    # ---------------------------------------------------------------
    # User input
    # ---------------------------------------------------------------

    with gr.Group(elem_id="ask-panel"):

        message = gr.Textbox(
            show_label=False,
            placeholder=(
                "Where would you like to go? "
                "For example: Plan me 3 days in Amsterdam..."
            ),
            lines=3,
        )

        success_criteria = gr.Textbox(
            show_label=False,
            placeholder=(
                "Success criteria — e.g. include timings, restaurants, "
                "walking/train distances and keep activities close together"
            ),
            lines=2,
        )

    # ---------------------------------------------------------------
    # Buttons
    # ---------------------------------------------------------------

    with gr.Row():

        reset_button = gr.Button(
            "Reset",
            elem_id="reset-button",
        )

        approve_button = gr.Button(
            "Approve and continue",
            visible=False,
            elem_id="approve-button",
        )

        go_button = gr.Button(
            "Plan my trip!",
            elem_id="go-button",
            interactive=False,
            variant="primary",
        )

    # Refresh TodoListMiddleware output every second
    timer = gr.Timer(1)

    # ---------------------------------------------------------------
    # Events
    # ---------------------------------------------------------------

    # Start Travel_App + MCP servers when page opens
    ui.load(
        setup,
        inputs=[],
        outputs=[
            travel_agent,
            go_button,
        ],
    )

    # Keep todo panel updating while agent works
    timer.tick(
        watch_todos,
        inputs=[travel_agent],
        outputs=[todos_panel],
        show_progress="hidden",
    )

    # Press enter in main request
    message.submit(
        process_message,
        inputs=[
            travel_agent,
            message,
            success_criteria,
            chatbot,
        ],
        outputs=[
            chatbot,
            approve_button,
            travel_agent,
        ],
    )

    # Press enter in success criteria
    success_criteria.submit(
        process_message,
        inputs=[
            travel_agent,
            message,
            success_criteria,
            chatbot,
        ],
        outputs=[
            chatbot,
            approve_button,
            travel_agent,
        ],
    )

    # Click Plan my trip
    go_button.click(
        process_message,
        inputs=[
            travel_agent,
            message,
            success_criteria,
            chatbot,
        ],
        outputs=[
            chatbot,
            approve_button,
            travel_agent,
        ],
    )

    # Approve HITL tool calls
    approve_button.click(
        approve,
        inputs=[
            travel_agent,
            chatbot,
        ],
        outputs=[
            chatbot,
            approve_button,
            travel_agent,
        ],
    )

    # Reset conversation
    reset_button.click(
        reset,
        inputs=[travel_agent],
        outputs=[
            message,
            success_criteria,
            chatbot,
            approve_button,
            travel_agent,
        ],
    )


if __name__ == "__main__":
    ui.launch(
        inbrowser=True,
        **LAUNCH_STYLE,
    )
