using DogRallyBlazorServer.Data;
using DogRallyBlazorServer.Models.Responses;
using Microsoft.EntityFrameworkCore;

namespace DogRallyBlazorServer.Services;

public interface ITrackService
{
    Task<GetAllTracksResponse> GetTracks();

}
public class TrackService : ITrackService
{
    private readonly IDbContextFactory<DataContext> _factory;

    public TrackService(IDbContextFactory<DataContext> factory)
    {
        _factory = factory;
    }
    
    
    public async Task<GetAllTracksResponse> GetTracks()
    {
        var response = new GetAllTracksResponse();

        try
        {
            using (var context = _factory.CreateDbContext())
            {
                var tracks = await context.Tracks.ToListAsync();
                response.Tracks = tracks;
                response.StatusCode = 200;
                response.Message = "Success";
            }
        }
        catch (Exception ex)
        {
            response.StatusCode = 500;
            response.Message = "Problemer med at hente banerne:" + ex.Message;
            response.Tracks = null;
        }

        return response;
    }
}

