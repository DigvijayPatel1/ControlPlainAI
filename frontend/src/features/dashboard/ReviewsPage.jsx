import { useReviewQueueQuery, useResolveReviewMutation } from './dashboardApi';
import { Empty, Panel } from './widgets';
export default function ReviewsPage() {
    const { data: reviews, isLoading, error } = useReviewQueueQuery();
    const [resolveReview, { isLoading: isResolving }] = useResolveReviewMutation();
    async function approve(reviewId) {
        await resolveReview({ reviewId, action: 'approve' });
    }
    return (<>
            <header className="mb-6">
                <p className="font-mono text-xs tracking-widest text-muted uppercase">Security centre / 03</p>
                <h1 className="mt-1 text-2xl font-semibold text-ink">Reviews</h1>
                <p className="mt-1 text-sm text-muted">Human review queue for flagged responses.</p>
            </header>

            {error && (<div className="mb-6 rounded-xl border border-brand-amber/30 bg-amber-50 px-4 py-3 text-sm text-brand-amber">
                    You need reviewer or admin access to see this queue.
                </div>)}

            <Panel title="Human review queue">
                {isLoading ? (<p className="text-sm text-muted">Loading…</p>) : reviews?.length ? (<div className="flex flex-col gap-4">
                        {reviews.map((review) => (<article key={review.review_id} className="rounded-xl border border-line p-4">
                                <div className="mb-2 flex items-center justify-between">
                                    <span className="rounded-full bg-amber-100 px-2 py-0.5 font-mono text-xs font-semibold text-brand-amber">
                                        Risk {review.risk_score.toFixed(2)}
                                    </span>
                                    <time className="text-xs text-muted">
                                        {new Date(review.created_at).toLocaleString()}
                                    </time>
                                </div>
                                <p className="mb-2 text-sm text-ink">{review.flagged_reason}</p>
                                <blockquote className="mb-3 rounded-lg border-l-4 border-line bg-paper px-3 py-2 text-sm text-muted italic">
                                    {review.proposed_response}
                                </blockquote>
                                <button type="button" disabled={isResolving} onClick={() => approve(review.review_id)} className="rounded-lg border border-brand-green px-3 py-1.5 text-sm font-medium text-brand-green transition-colors hover:bg-mint disabled:opacity-50">
                                    Approve {review.review_id.slice(0, 8)}
                                </button>
                            </article>))}
                    </div>) : (<Empty text="No pending reviews."/>)}
            </Panel>
        </>);
}
