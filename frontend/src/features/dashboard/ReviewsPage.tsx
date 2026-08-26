import { useReviewQueueQuery, useResolveReviewMutation } from './dashboardApi'
import { Empty, Panel } from './widgets'

export default function ReviewsPage() {
    const { data: reviews, isLoading, error } = useReviewQueueQuery()
    const [resolveReview, { isLoading: isResolving }] = useResolveReviewMutation()

    async function approve(reviewId: string) {
        await resolveReview({ reviewId, action: 'approve' })
    }

    return (
        <>
            <header className="topbar">
                <div>
                    <p className="eyebrow">SECURITY CENTRE / 03</p>
                    <h1>Reviews</h1>
                    <p className="muted">Human review queue for flagged responses.</p>
                </div>
            </header>
            {error && <div className="notice">You need reviewer or admin access to see this queue.</div>}
            <Panel title="Human review queue">
                {isLoading ? (
                    <p className="muted">Loading…</p>
                ) : (
                    <div className="review-list">
                        {reviews?.length ? (
                            reviews.map((review) => (
                                <article className="review" key={review.review_id}>
                                    <div className="review-head">
                                        <span className="badge amber">Risk {review.risk_score.toFixed(2)}</span>
                                        <time>{new Date(review.created_at).toLocaleString()}</time>
                                    </div>
                                    <p>{review.flagged_reason}</p>
                                    <blockquote>{review.proposed_response}</blockquote>
                                    <button className="outline" disabled={isResolving} onClick={() => approve(review.review_id)}>
                                        Approve {review.review_id.slice(0, 8)}
                                    </button>
                                </article>
                            ))
                        ) : (
                            <Empty text="No pending reviews." />
                        )}
                    </div>
                )}
            </Panel>
        </>
    )
}